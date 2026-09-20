# USER STORY: RCAT → Recred Updates — a Full Termination selected by the PDM Specialist is silently downgraded to a Convert-to-Non-Participating termination, even when the practitioner has no PNC or Delegated locations

> Authored with the **User Story Solution Architect** (v1.11). Vertical: **Provider Network Management (PNM)**. Workflow mode: **Bug Fix**.
> **Component-graph note:** the `code-review-graph` MCP was unavailable during this session, so every OmniScript element, set-values step, and picklist option cited below was verified by direct metadata inspection of the **active** `PRM_PractitionerTerminationRecredForm_English` v4 XML — exact line numbers are called out in **Current State**.
> **Sibling story cross-reference:** [`RCAT_PNCOnlyPractitioner_NotFlagged_UserStory.md`](RCAT_PNCOnlyPractitioner_NotFlagged_UserStory.md) (AC-20 – AC-23) already touches the same OmniScript from the **opposite** angle — it *restricts* the choice to "Convert to Non-Participating" for LMS + PNC/Delegated practitioners. This story is its **inverse**: it fixes the case where a practitioner has **no** PNC/Delegated location, the PDM Specialist explicitly picks a Full Termination, and the form silently converts it anyway. Both are needed and both touch the same OmniScript and the same `FullTermination` picklist — **sequence them together, in one new active version**, so the two conditionals live in the same script and cannot fight.

**Persona:** PDM Specialist (works the round-robin `Type = Recred Updates` case handed off from RCAT)
**Priority:** P0 (production defect — legitimate Full Terminations cannot be submitted; practitioner records that should be effective-dated closed and cleared of `PRM_NonParticipatingStartDate__c` are being flagged Non-Par instead)
**OmniScript (defect surface):** `PRM_PractitionerTerminationRecredForm_English` **v4 (active)**
**Integration Procedures (downstream, unchanged by this story but verified as the consumer of the corrected write):** `PRM_PractitionerTerminationRecordsRecredUpdate_Procedure` (v10)
**Apex (downstream, unchanged):** `PRM_FullPracTermRecredBatchService`, `PRM_RCATTerminationBatchHelper.processPractitioners` (the shared account write called from the Full-Termination cascade)
**Key OmniScript elements:** `FullTermination` picklist (level 1.0, sequence within its parent step) · `SVTerminationTypeSelected` (Set Values, sequence 8.0) · `SV_FullTermination` (Set Values, `SubType = FullTermination`) · `SV_FullTerminationNonPar` (Set Values, `SubType = Non Par Conversion`) · `CheckAndProcessNonPar` (IP action, sequence 16.0, consumes `FullTermination` via `%FullTerminationSelected%`)
**Relevant Requirements:** `RCAT_PNCOnlyPractitioner_NotFlagged_UserStory.md` (inverse restriction — same field), `RCAT_PracticeLocation_NonPar_FullTerm_Batch_UserStory.md` (uses the same Full-Term-vs-Non-Par distinction on the RCAT auto-batch side, driven by Termination Reason rather than by this picklist), `OmniScript_StaleActiveVersions_SourceHygiene_UserStory.md` (prerequisite — reconcile stale `isActive` flags on this OmniScript before deploying a new version)

---

## Story

**As a** PDM Specialist working the round-robin `Recred Updates` case that RCAT hands off,
**I want** the termination action I select on the Recred Updates form to be the action the system actually performs — so that when I choose **Full Termination** for a practitioner whose remaining practice locations are neither PNC nor Delegated, the practitioner is fully terminated rather than converted to Non-Participating,
**So that** the practitioner's record ends up in the state the business decided on (fully effective-dated closed with no `Non-Participating Start Date` and the Full-Termination downstream cascade run) instead of the Non-Par state (still participating but marked non-par with a `Non-Participating Start Date`) that PDM has to unwind by hand.

---

## Why it matters

**The two outcomes are not interchangeable.** A **Full Termination** effective-dates the practitioner closed and runs the Full-Termination cascade downstream in `PRM_PractitionerTerminationRecordsRecredUpdate_Procedure` — practice-to-practitioner, practice-location-to-practitioner, practice location taxonomy, location network, and location tax network are all closed. A **Convert to Non-Participating** leaves the practitioner *still active* on the practice locations, sets `Non-Participating Start Date` on the practitioner and account, and runs none of that cascade. Silently swapping one for the other means the practitioner keeps affiliations, networks, and taxonomy the business decided to end — a directory-accuracy and claims-integrity problem PDM has to detect after the fact and undo manually. The defect also erodes trust in the guided flow itself: the Specialist sees two options that look identical on screen, picks one, and gets the other.

**Why it is P0.** Every Full Termination submitted through this form since v4 shipped has been silently downgraded, because the overwrite step (`SVTerminationTypeSelected`, sequence 8.0) runs on every submission with no guard. There is no user action that avoids it — training the specialist cannot fix this bug.

---

## Scope

| Flow | Component | Affected step | Data source |
|---|---|---|---|
| PDM works the Recred Updates case | `PRM_PractitionerTerminationRecredForm_English` v4 | `FullTermination` picklist (the two-identical-label defect) | Reviewer input |
| PDM works the Recred Updates case | `PRM_PractitionerTerminationRecredForm_English` v4 | `SVTerminationTypeSelected` (sequence 8.0) — the unconditional overwrite | Hard-coded `"Convert to Non-Participating"` at line 4348 |
| PDM works the Recred Updates case | `PRM_PractitionerTerminationRecredForm_English` v4 | `SV_FullTermination` / `SV_FullTerminationNonPar` (the two mutually-exclusive branches gated on `FullTermination`) | The selected value |
| PDM works the Recred Updates case | `CheckAndProcessNonPar` action (sequence 16.0) | Payload key `FullTermination` = `%FullTerminationSelected%` sent to the downstream IP | Formula computed from `EffectiveTo` |

**In scope:**
- `PRM_PractitionerTerminationRecredForm_English` — cut a **new active version** (v5) that (a) relabels the two `FullTermination` options so they are distinguishable and (b) either removes the unconditional overwrite in `SVTerminationTypeSelected` or replaces it with a conditional that only fires for the LMS + PNC/Delegated case owned by the sibling story.
- Regression pass on both branches (Full Termination and Convert-to-Non-Participating) end to end, including the downstream IP.

**Out of scope:**
- The downstream IP `PRM_PractitionerTerminationRecordsRecredUpdate_Procedure` (v10). Its Full-Termination cascade already exists (`Type == 'Full Practitioner Termination' && SubType == 'FullTermination'`) and is the path that today never fires. No change needed there; only regression.
- The RCAT auto-batch path (`PRM_RCATLocationTerminationBatch` / `PRM_RCATNetworkTerminationBatch`) — Full-Term vs Non-Par on that path is derived from Termination Reason (`FULLTERMREASON`), not from this OmniScript field, so the defect does not exist there. Confirmed under Clarification #4.
- The Partial Termination flow (`SV_PartialTermination`) — the `FullTermination` field does not gate the partial branch.
- All PNC / Delegated / Credentialing Status / Recred Due Date rules — owned by the sibling story.

---

## Current State (from codebase)

### The defect — one field, three cooperating bugs, one guaranteed outcome

All line references below are the **active** `PRM_PractitionerTerminationRecredForm_English_4.os-meta.xml`.

**Bug 1 — the picklist has two options with the identical display label** (`FullTermination` field, level 1.0, lines 2683–2707):

```
"name" : "FullTermination",
"defaultValue" : "Convert to Non-Participating",
"options" : [
  { "name" : "Convert to Non-Participating", "value" : "Full-Termination" },
  { "name" : "Convert to Non-Participating", "value" : "Convert to Non-Participating" }
]
```

Both options render as *"Convert to Non-Participating"* on screen. The Specialist cannot distinguish them, and — because the default is `"Convert to Non-Participating"` — the two visible options both look like the default.

**Bug 2 — an unconditional Set Values step clobbers whatever the Specialist selected** (`SVTerminationTypeSelected`, sequence 8.0, lines 4337–4360):

```
"elementValueMap" : {
  "IsDelegationTerminationSelected" : "=IF(%TerminationType% == 'Delegation Termination', true, false)",
  "isTermTypeBlank"                : "=IF(%TerminationType% == NULL, true, false)",
  "FullTermination"                : "Convert to Non-Participating"
},
"show" : null
```

`"show" : null` means no visibility rule, and no `merge`/`skip-if-set` guard. The step runs on every submission and overwrites `FullTermination` to the literal string `"Convert to Non-Participating"` — which is one of the two picklist values, so the branch gates downstream still see a "valid" selection.

**Bug 3 — the two mutually-exclusive branch steps gate on that overwritten value.** `SV_FullTermination` (lines 4062–4130) fires only when `FullTermination = "Full-Termination"` and writes `Type = "Full Practitioner Termination"`, `SubType = "FullTermination"`. `SV_FullTerminationNonPar` (lines 4137–4210) fires only when `FullTermination = "Convert to Non-Participating"` and writes `SubType = "Non Par Conversion"`. Because Bug 2 hard-codes the value to `"Convert to Non-Participating"`, **only the Non-Par branch is reachable**, and the `SV_FullTermination` step at sequence 19.0 is effectively dead code in the running version.

**Downstream consequence.** `CheckAndProcessNonPar` at sequence 16.0 sends `"FullTermination" : "%FullTerminationSelected%"` (a formula variable, `IF(%EffectiveTo% != NULL, true, false)` — line 4322) to the IP, so *whether the practitioner should be terminated at all* survives; but the *type* of termination decided by the `SV_*` steps and passed to `PRM_PractitionerTerminationRecordsRecredUpdate_Procedure` is always Non-Par. The v10 IP's Full-Termination cascade branch (`Type == 'Full Practitioner Termination' && SubType == 'FullTermination'`, documented in the sibling story) is never invoked.

### Why "no PNC / Delegated location" matters here

The sibling story's AC-20 – AC-23 says: for practitioners with **an LMS location AND a PNC/Delegated location**, we *want* to restrict the choice to "Convert to Non-Participating" — a genuine Full Termination is business-invalid for them because they legitimately keep participating at the PNC/Delegated location. The mechanism that will implement that restriction is exactly the `SVTerminationTypeSelected` overwrite (or its successor conditional).

The defect is that the overwrite exists **for every practitioner**, not only for the qualifying LMS + PNC/Delegated one. A practitioner whose every active location is neither PNC nor Delegated is precisely the practitioner for whom Full Termination is the business-correct action. Today, the overwrite silently converts them to Non-Par anyway.

### What is *not* broken

- The picklist wiring, the downstream IP action call, the formula variable `%FullTerminationSelected%`, and both `SV_*` branch steps' record-to-upsert payloads are all correct. The Full-Termination payload is complete and would produce the right cascade if it ever ran.
- The RCAT auto-batch path (non-LMS) does not consume this picklist — it derives Full-Term-vs-Non-Par from Termination Reason (`PRM_RCATTerminationBatchHelper` and the `FULLTERMREASON` constant). The defect is scoped to this OmniScript.

---

## Acceptance Criteria

**AC-1 — The two termination choices are distinguishable on screen (happy path)**

**Given** a PDM Specialist opens the Recred Updates termination screen for any practitioner,
**When** the termination-type choice is displayed,
**Then** each of the two options carries a distinct, self-explanatory label,
**And** the option that performs a Full Termination is labelled honestly (for example, *"Full Termination"*), and only the Non-Participating option is labelled *"Convert to Non-Participating"*,
**And** the Specialist can tell from the labels alone which action each choice performs.

**AC-2 — A Full Termination selected for a practitioner with no PNC or Delegated location is honoured**

**Given** a PDM Specialist working a Recred Updates case for a practitioner whose every remaining active practice location is neither PNC nor Delegated,
**And** the Specialist selects Full Termination on the termination-type choice,
**When** the Specialist submits the form,
**Then** the practitioner is fully terminated in the downstream cascade,
**And** the practitioner's participating code is left cleared rather than being set to Non-Par,
**And** the practitioner's Non-Participating Start Date is left blank rather than being written,
**And** the practitioner's Full-Termination cascade (practice-to-practitioner, practice-location-to-practitioner, location taxonomy, location network, location tax network) runs.

**AC-3 — A Convert-to-Non-Participating decision still runs the Non-Par branch (no regression)**

**Given** a PDM Specialist working a Recred Updates case,
**And** the Specialist selects Convert to Non-Participating,
**When** the Specialist submits the form,
**Then** the practitioner is set to Non-Participating with a Non-Participating Start Date exactly as they are today,
**And** the Full-Termination cascade does **not** run,
**And** the outcome is byte-for-byte identical to what the form produces today for that same selection.

**AC-4 — The unconditional overwrite of the selected choice is removed**

**Given** the Recred Updates form has been submitted with either termination-type choice,
**When** the OmniScript reaches the point where it decides which of the two branch steps to run,
**Then** the value the Specialist selected is the value used to decide the branch,
**And** no earlier step in the OmniScript has overwritten that value on its own — a step may only overwrite the choice under an explicit visibility rule tied to the sibling-story restriction (see AC-6 and Clarification #1),
**And** the branch that runs is the one whose value gate matches the Specialist's selection.

**AC-5 — The Specialist cannot leave the choice unanswered (edge case)**

**Given** a PDM Specialist has opened the Recred Updates termination screen but has not selected a termination type,
**When** the Specialist tries to submit the form,
**Then** submission is blocked and the Specialist is prompted to choose Full Termination or Convert to Non-Participating,
**And** neither `SV_*` branch step runs until the choice is made,
**And** the default value on the field is either removed or set to a value that does not satisfy either branch's gate, so that "not answered" is a distinct state from "Convert to Non-Participating".

**AC-6 — The sibling-story restriction is not broken by this fix (dependency)**

**Given** a practitioner who has at least one LMS practice location and at least one PNC or Delegated practice location (the practitioner the sibling story restricts),
**When** the PDM Specialist opens the Recred Updates termination screen for that practitioner,
**Then** the Full Termination choice is either hidden or shown-and-disabled per the sibling story's AC-21 decision,
**And** the mechanism that enforces that restriction is a conditional visibility or option-render rule keyed to the practitioner's location mix — **not** the unconditional overwrite this story removes.

**AC-7 — Partial Termination is unaffected (negative)**

**Given** a PDM Specialist working a Recred Updates case who selects a Partial Termination (Practice Locations, Assigned Networks, Info Codes, or any combination),
**When** the Specialist submits the form,
**Then** the Partial-Termination branch (`SV_PartialTermination`) runs exactly as it does today,
**And** none of this story's changes affect a partial-termination outcome.

**AC-8 — Downstream IP receives the corrected `SubType` and runs the matching cascade (integration)**

**Given** a PDM Specialist submits the form with either termination-type choice for a practitioner in scope,
**When** `PRM_PractitionerTerminationRecordsRecredUpdate_Procedure` is invoked with the OmniScript's payload,
**Then** the `SubType` in the payload matches the Specialist's on-screen choice one-for-one — `FullTermination` when Full Termination was selected, `Non Par Conversion` when Convert to Non-Participating was selected,
**And** the IP runs the cascade branch that matches that `SubType`, with no downstream re-force back to Non-Par.

---

### Pattern E — Record & Field Specification

The Recred Updates form ultimately writes the same practitioner Person Account and Case Manager the sibling story covers; only the `Type` / `SubType` on the payload — and therefore which downstream cascade runs — changes here. Two `SV_*` steps are the write. Every field in each payload is enumerated.

**AC-9 — Payload written by `SV_FullTermination` when the Specialist selects Full Termination**

**Given** a PDM Specialist selects Full Termination on the Recred Updates form and submits,
**When** the OmniScript reaches the branch selector,
**Then** exactly the following payload is emitted (no other `SV_*` termination-type step fires):

**`RecordToUpsert` — Set Values `SV_FullTermination`**

| Field | Value | Notes |
|---|---|---|
| `Type` | `Full Practitioner Termination` | Unchanged |
| `SubType` | `FullTermination` | **Now actually reachable — this is the bug's outcome** |
| `EffectiveTo` | `%EffectiveToTemp%` | Unchanged |
| `Pending` | `false` | Unchanged |
| `IsErrorRecord` | `false` | Unchanged |
| `CaseToBeUpdated` | `%ContextId%` | Unchanged |
| `HCFNetworks` | `%PracticeLocationNw%` | Unchanged |
| `HealthcareProviderNPI` | `%IpRepsonse:HealthCareProviders:NpiId%` | Unchanged |
| `HealthcareProviderNPIEffFrom` | `%IpRepsonse:HealthCareProviders:EffectiveFrom%` | Unchanged |
| `InfoCodeAssignment` | `%InfoCodes%` | Unchanged |
| `PractitionerIdentifier` | `%PractitionerIdentifier%` | Unchanged |
| `PractitionerPracticeLocation` | `%SearchResults:PracticeLocations%` | Unchanged |
| `Practitioner.Id` | `%IpRepsonse:HealthCareProviders:AccountId%` | Unchanged |
| `Practitioner.ContactId` | `%IpRepsonse:HealthCareProviders:Account:ContactId%` | Unchanged |
| `Practitioner.EffectiveTo` | `%EffectiveTo%` | Unchanged |
| `Practitioner.PRM_CaseManager__c` | `%RecredCaseManagerId%` | Unchanged |
| `Practitioner.PracEffecFrom` | `%SearchResults:EffectiveFrom%` | Unchanged |
| `Case.AccountId` | `%IpRepsonse:HealthCareProviders:AccountId%` | Unchanged |
| `Case.ContactId` | `%IpRepsonse:HealthCareProviders:Account:ContactId%` | Unchanged |
| `Case.IsRoundRobinLogic` | `true` | Unchanged |
| `Case.RecordTypeName` | `PRM_PRM` | Unchanged |
| `Case.Status` | `New` | Unchanged |
| `Case.Type` | `Network Management QC` | Unchanged |
| `CaseManager.Id` | `%RecredCaseManagerId%` | Unchanged |
| `CaseManager.PDMManualUpdate` | `Practitioner Termination` | Unchanged |
| `CaseManager.RecordTypeName` | `PRM_ReCredentialing` | Unchanged |
| `CaseManager.Stage` | `Network Management QC` | Unchanged |
| `CaseManager.Status` | `In Progress` | Unchanged |
| `CaseManager.TerminationDate` | `%EffectiveToTemp%` | Unchanged |
| `CaseManager.TerminationReason` | `%TerminationReason%` | Unchanged |
| `CaseManager.TerminationType` | `%TerminationType%` | Unchanged |

**Fields the step must NOT write:** `Practitioner.ParticipatingCode`, `Practitioner.Non-ParticipatingStartDate` — these belong to the Non-Par branch only and their absence from the Full-Termination payload is what makes the two outcomes different.

**AC-10 — Payload written by `SV_FullTerminationNonPar` when the Specialist selects Convert to Non-Participating**

**Given** a PDM Specialist selects Convert to Non-Participating and submits,
**When** the OmniScript reaches the branch selector,
**Then** exactly the following payload is emitted (no other `SV_*` termination-type step fires):

**`RecordToUpsert` — Set Values `SV_FullTerminationNonPar`**

| Field | Value | Notes |
|---|---|---|
| `Type` | `Full Practitioner Termination` | Unchanged |
| `SubType` | `Non Par Conversion` | Unchanged |
| `EffectiveTo` | `%EffectiveTo%` | Unchanged |
| `Pending` | `false` | Unchanged |
| `IsErrorRecord` | `false` | Unchanged |
| `CaseToBeUpdated` | `%ContextId%` | Unchanged |
| `HCFNetworks` | `%PracticeLocationNw%` | Unchanged |
| `HealthcareProviderNPI` | `%IpRepsonse:HealthCareProviders:NpiId%` | Unchanged |
| `HealthcareProviderNPIEffFrom` | `%IpRepsonse:HealthCareProviders:EffectiveFrom%` | Unchanged |
| `InfoCodeAssignment` | `%InfoCodes%` | Unchanged |
| `PractitionerPracticeLocation` | `%SearchResults:PracticeLocations%` | Unchanged |
| `Practitioner.Id` | `%IpRepsonse:HealthCareProviders:AccountId%` | Unchanged |
| `Practitioner.ContactId` | `%IpRepsonse:HealthCareProviders:Account:ContactId%` | Unchanged |
| `Practitioner.Non-ParticipatingStartDate` | `%EffectiveTo%` | Unchanged |
| `Practitioner.ParticipatingCode` | `Non-Par` | Unchanged |
| `Practitioner.PRM_CaseManager__c` | `%RecredCaseManagerId%` | Unchanged |
| `Practitioner.PracEffecFrom` | `%SearchResults:EffectiveFrom%` | Unchanged |
| `Case.AccountId` | `%IpRepsonse:HealthCareProviders:AccountId%` | Unchanged |
| `Case.ContactId` | `%IpRepsonse:HealthCareProviders:Account:ContactId%` | Unchanged |
| `Case.IsRoundRobinLogic` | `true` | Unchanged |
| `Case.RecordTypeName` | `PRM_PRM` | Unchanged |
| `Case.Status` | `New` | Unchanged |
| `Case.Type` | `Network Management QC` | Unchanged |
| `CaseManager.Id` | `%RecredCaseManagerId%` | Unchanged |
| `CaseManager.PDMManualUpdate` | `Non-Par Practitioner Conversion` | Unchanged |
| `CaseManager.RecordTypeName` | `PRM_ReCredentialing` | Unchanged |
| `CaseManager.Stage` | `Network Management QC` | Unchanged |
| `CaseManager.Status` | `In Progress` | Unchanged |
| `CaseManager.TerminationDate` | `%EffectiveTo%` | Unchanged |
| `CaseManager.TerminationReason` | `%TerminationReason%` | Unchanged |
| `CaseManager.TerminationType` | `%TerminationType%` | Unchanged |

**Elements explicitly NOT touched by this story**

| Element | Reason |
|---|---|
| `SV_PartialTermination` | Partial-Termination branch is out of scope (AC-7) |
| `CheckAndProcessNonPar` (sequence 16.0) — its `%FullTerminationSelected%` formula | Formula computes *whether an EffectiveTo was entered*, not the termination type; unchanged |
| `PRM_PractitionerTerminationRecordsRecredUpdate_Procedure` v10 | Downstream cascade branches are already correctly gated on `SubType`; only regression |
| `PRM_RCATLocationTerminationBatch` / `PRM_RCATNetworkTerminationBatch` | RCAT auto-batch path does not consume this picklist |

---

## Technical Implementation (high-level)

> The whole story lands in **one new active version** of `PRM_PractitionerTerminationRecredForm_English` (v5). Do **not** edit v4 in place. Coordinate the deployment with the sibling story so both changes ship on the same version — otherwise the two conditionals will contradict each other on the same field.

| Component | Type | Change | Drives |
|---|---|---|---|
| `PRM_PractitionerTerminationRecredForm_English` **v4 → new v5** | New active OmniScript version | Cut a new version; base on v4; reconcile the source-hygiene issue flagged in `OmniScript_StaleActiveVersions_SourceHygiene_UserStory.md` (v4 marked active alongside a stale version) before deployment. | AC-1 – AC-10 |
| `FullTermination` picklist (level 1.0, lines 2683–2707 in v4) | Modified OmniScript element | (a) **Relabel** the `Full-Termination`-valued option so it no longer reads `Convert to Non-Participating` — e.g. `name` = `Full Termination`. (b) Remove or change the `defaultValue` so that the field is not pre-selected to a real option, so AC-5 can enforce the "must choose" requirement. | AC-1, AC-5 |
| `SVTerminationTypeSelected` (Set Values, sequence 8.0, lines 4337–4360 in v4) | Modified OmniScript step | Remove the `"FullTermination" : "Convert to Non-Participating"` entry from `elementValueMap` — or, if the sibling-story restriction reuses this step, wrap it in a `show` visibility rule keyed to the practitioner's location mix (LMS + PNC/Delegated), so it only overwrites when AC-6 says it should. Preserve the other two entries (`IsDelegationTerminationSelected`, `isTermTypeBlank`) unchanged. | AC-2, AC-4, AC-6 |
| `SV_FullTermination` (Set Values, sequence 19.0, lines 4062–4130 in v4) | Verify | No change to the step's payload or gate; verify it is now reachable end-to-end. | AC-2, AC-8, AC-9 |
| `SV_FullTerminationNonPar` (Set Values, lines 4137–4210 in v4) | Verify | No change; verify byte-for-byte parity with today for the Convert-to-Non-Participating branch. | AC-3, AC-8, AC-10 |
| `CheckAndProcessNonPar` (IP action, sequence 16.0, lines 15–80 in v4) | Verify | No change; the `%FullTerminationSelected%` extra-payload key is a formula (`IF(%EffectiveTo% != NULL, true, false)`) that answers *"is there a termination at all?"* and is independent of the type. Regression only. | AC-8 |
| `PRM_PractitionerTerminationRecordsRecredUpdate_Procedure` (v10) | Verify | Its Full-Termination cascade branch is gated on `Type == 'Full Practitioner Termination' && SubType == 'FullTermination'` and already exists. Regression run only — confirm no other step in the IP re-forces the payload back to Non-Par when `SubType = FullTermination`. | AC-8 |
| Recred termination form tests (new + modified) | OmniScript / IP regression | Cover (i) Full Termination selected → Full-Termination cascade fires and Non-Par fields not written, (ii) Convert to Non-Participating selected → byte-for-byte parity with today, (iii) no selection → submit blocked, (iv) LMS + PNC/Delegated practitioner still sees the sibling-story restriction, (v) Partial Termination unaffected. | AC-1 – AC-10 |

**Notes for the developer:**

- **This defect is caused by three cooperating bugs, not one.** Fixing only the label collision (Bug 1) is not enough — `SVTerminationTypeSelected` still overwrites the choice. Fixing only the overwrite is not enough either — the two option labels are still indistinguishable and the default still lands on Non-Par. Fix all three in the same version.
- **The overwrite step also does two innocent things** (`IsDelegationTerminationSelected` and `isTermTypeBlank`). Do not delete the whole step — remove only the `FullTermination` entry from its `elementValueMap`, or wrap the whole step in a visibility rule tied to the sibling-story restriction.
- **Coordinate the sibling story now, not later.** If the sibling story ships first with a *new* conditional overwrite in `SVTerminationTypeSelected` and this story ships next removing that overwrite, the sibling's restriction is destroyed. If this story ships first and the sibling adds an unconditional overwrite back in, this story regresses. Either merge them into a single version release, or agree in the code review which conditional lives in the shipped step.
- **`defaultValue` is part of the defect.** Because `defaultValue = "Convert to Non-Participating"` is also one of the two option values, the field is always "answered" from the Specialist's point of view. Removing the default is what turns "not answered" into a distinct state and lets AC-5 do its job.
- **Verify the OmniScript compiles and re-activates.** Two `isActive=true` versions on the same OmniScript is a real risk on this file (see `OmniScript_StaleActiveVersions_SourceHygiene_UserStory.md`). Confirm exactly one active version after deployment.
- **Downstream is a regression pass, not new code.** The Full-Termination cascade in the v10 IP is the code path the sibling story documents; no change required, only proof it fires end-to-end when the form emits the corrected `SubType`.

---

## Definition of done

- [ ] A PDM Specialist opening the Recred Updates termination screen sees two distinctly-labelled choices, and can tell from the labels alone which one performs a Full Termination (AC-1) — verified in QA on a real case.
- [ ] For a practitioner whose every active practice location is neither PNC nor Delegated, selecting Full Termination fully terminates the practitioner and does **not** set `Non-Participating Start Date` (AC-2) — verified in QA on a real case with `Non-Participating Start Date` observed blank in field history.
- [ ] Selecting Convert to Non-Participating is byte-for-byte identical to today's Non-Par outcome (AC-3) — parity confirmed on a QA reproducer.
- [ ] No step in the OmniScript overwrites the Specialist's selected value on its own — any overwrite is gated by a visibility rule keyed to the sibling-story restriction (AC-4).
- [ ] Submitting the form with no termination-type selected is blocked (AC-5).
- [ ] The sibling story's LMS + PNC/Delegated restriction still enforces "Convert to Non-Participating only" for those practitioners (AC-6) — regression on both stories run together on the same OmniScript version.
- [ ] Partial-Termination submissions are unaffected (AC-7) — regression run on all four Partial-Termination combinations.
- [ ] The downstream IP receives `SubType = FullTermination` when Full Termination is selected and `SubType = Non Par Conversion` when Convert to Non-Participating is selected, and runs the matching cascade (AC-8, AC-9, AC-10) — verified against IP logs on a QA case.
- [ ] Exactly one active version of `PRM_PractitionerTerminationRecredForm_English` in the org after deployment (source-hygiene prerequisite).
- [ ] New OmniScript version cut rather than editing v4 in place.
- [ ] Cross-referenced from `RCAT_PNCOnlyPractitioner_NotFlagged_UserStory.md` (add a "Related User Stories" bullet on that file pointing back here) so the two are visibly co-owners of the same OmniScript version.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | **Merge with the sibling story or ship separately?** The sibling story's AC-21 will reuse `SVTerminationTypeSelected` as its restriction mechanism. If we ship this story first and remove the overwrite, the sibling story must reintroduce a *conditional* overwrite in the same step. Easier to ship them together on one OmniScript version. | Delivery sequencing and merge-conflict risk on the same OmniScript version | BA / Technical |
| 2 | **Should the Full Termination option be hidden or shown-and-disabled for the sibling-story qualifier?** (Same question as sibling story's Clarification #17.) Whichever mechanism we choose has to coexist with this story's fix — hidden via option-render filter, or shown-and-disabled with a tooltip. | UX + how the two stories cooperate | BA / UX |
| 3 | **Is the term "Full Termination" the right business label,** or does the business prefer "Fully Terminate", "Terminate", or another phrasing? The current option's *value* is `Full-Termination` (hyphenated); the display label is what changes. | Directly worded on-screen — Specialist comprehension | BA / Product |
| 4 | **Does the same overwrite defect exist on the RCAT-side auto-batch path?** The RCAT batch derives Full-Term vs Non-Par from `FULLTERMREASON` (Termination Reason), not from this picklist, so we believe it does not. Confirm before ruling the RCAT path out of scope. | Whether a companion story is needed for the auto-batch path | Technical |
| 5 | **Should the fix be back-applied to any case already downgraded in flight?** A `Recred Updates` case that PDM submitted last week as Full Termination but that landed as Non-Par may need a manual correction pass. Similar in spirit to the sibling story's AC-12 backfill, but scoped to submissions since v4 shipped. | Whether a data-fix follow-up is needed | Ops / Credentialing |
| 6 | **`defaultValue` — remove entirely or replace with a placeholder like `Please select` that satisfies neither branch?** Either satisfies AC-5, but a placeholder gives the Specialist a nudge instead of a blank field. | Small UX detail | BA / UX |
| 7 | **Confirm the active version of `PRM_PractitionerTerminationRecredForm_English`.** Source has v1–v4; v4 is marked active. Sibling story flagged a stale-active-version risk on this OmniScript's parent (`PRM_ReviewRCAT_English`, v8 vs v10) — do not repeat that on this file when cutting v5. | Prevents the source-hygiene regression | Technical |
| 8 | **Should any server-side validation refuse a payload where `SubType = FullTermination` arrives for a practitioner the sibling story restricts?** UI-only enforcement can be bypassed by direct IP calls. (Same as sibling story's Clarification #16.) | Whether server-side validation is needed | Technical / Security |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_PractitionerTerminationRecredForm_English` v4 → v5 | OmniScript | HIGH | The whole fix lives here. Two elements change (`FullTermination` picklist + `SVTerminationTypeSelected` Set Values); a third is regression-only (`SV_FullTermination`). |
| `PRM_PractitionerTerminationRecordsRecredUpdate_Procedure` v10 | Integration Procedure | MEDIUM | The Full-Termination cascade branch, previously unreachable in practice, is now reached on every legitimate Full Termination. Regression only — no change to the IP. |
| `PRM_FullPracTermRecredBatchService`, `PRM_RCATTerminationBatchHelper.processPractitioners` | Apex | MEDIUM | Downstream consumers of the Full-Termination cascade. Regression only. |
| `PRM_ReviewRCAT_English` v10 / `PRM_RCATProcessingController` / `PRM_RCATLocationTerminationBatch` | OmniScript / Apex | LOW | Not consumed by this picklist. Regression pass on RCAT-side full termination confirms independence from this fix. |
| `SV_PartialTermination` | OmniScript element | LOW | Not gated on `FullTermination`. Regression pass on all Partial-Termination combinations. |
| `Account` (Practitioner Person Account) fields — `PRM_NonParticipatingStartDate__c`, `ParticipatingCode`, `PRM_CaseManager__c`, effective-dating fields | Fields | HIGH | Values are now correct on Full-Term submissions — the whole point of the fix. |
| Recred termination flow tests + OmniScript regression suite | Tests | HIGH | Needs new assertions for AC-1 through AC-10 including both branches, no-selection, LMS + PNC/Delegated coexistence, Partial-Termination isolation. |

---

## Estimated Effort *(AI-estimated — validate with team)*

| Component | Change Type | Effort | Notes |
|-----------|-------------|--------|-------|
| Cut new active version of `PRM_PractitionerTerminationRecredForm_English` (v5) | OmniScript version | S | Base on v4; do not edit v4 in place |
| Relabel the `FullTermination` picklist option and remove/adjust `defaultValue` | OmniScript element | S | Two-line change; no formula rework |
| Remove the `FullTermination` entry from `SVTerminationTypeSelected` (or wrap the step in a visibility rule if merging with the sibling story) | OmniScript Set Values | S | Coordinated design decision with sibling story (Clarification #1) drives whether this is a delete or a conditional |
| End-to-end regression on both branches through `PRM_PractitionerTerminationRecordsRecredUpdate_Procedure` v10 | QA | M | Two happy paths + no-selection + Partial-Termination + LMS + PNC/Delegated restriction |
| Sibling-story coexistence check | QA / Technical | S | Prove one OmniScript version satisfies both stories simultaneously |
| Source-hygiene reconciliation of the OmniScript's active-version flags | Source hygiene | S | Prerequisite; not optional |
| Downstream data-fix / correction pass on already-downgraded submissions | Ops + optional Apex | M–L | Only if Clarification #5 says yes; otherwise not needed |
| Tests: OmniScript / IP regression + assertions on the practitioner write for both branches | Tests | M | Assert `PRM_NonParticipatingStartDate__c`, `ParticipatingCode`, and `SubType` explicitly |

**Total Estimated Effort:** **M** (≈5 story points) — the fix itself is three small OmniScript edits, but the coordination overhead with the sibling story and the two-branch regression pass make it more than a trivial S. Slot the two stories into the same sprint so both changes ride the same OmniScript version.

---

## Related User Stories

- [`RCAT_PNCOnlyPractitioner_NotFlagged_UserStory.md`](RCAT_PNCOnlyPractitioner_NotFlagged_UserStory.md) — **inverse rule on the same picklist.** Its AC-20 – AC-23 restrict the Full Termination choice for LMS + PNC/Delegated practitioners; this story fixes the case where no such restriction should apply. **Ship together on one OmniScript version** (Clarification #1). Its AC-23 already flagged the duplicate-label defect this story finishes.
- [`RCAT_PracticeLocation_NonPar_FullTerm_Batch_UserStory.md`](RCAT_PracticeLocation_NonPar_FullTerm_Batch_UserStory.md) — sibling batch story that derives Full-Term vs Non-Par from Termination Reason (`FULLTERMREASON`). Confirms the RCAT auto-batch path is not affected by this defect (Clarification #4).
- [`OmniScript_StaleActiveVersions_SourceHygiene_UserStory.md`](OmniScript_StaleActiveVersions_SourceHygiene_UserStory.md) — **prerequisite.** Reconcile any stale `isActive=true` flags on `PRM_PractitionerTerminationRecredForm_English` before cutting v5.
- [`Recred_GuidedFlow_to_ReCredPDA_Routing_Audit_2026-06-08.md`](Recred_GuidedFlow_to_ReCredPDA_Routing_Audit_2026-06-08.md) — background on the Recred Updates round-robin routing that lands the case in front of the PDM Specialist.
