# USER STORY US-RC1: RCAT termination does not flag a practitioner as PNC when all of their practice locations are PNC — PNC / Delegated practitioners must be left with no credentialing status and no recred due date — and an LMS + PNC/Delegated practitioner must be restricted to "Convert to Non-Participating"

> Authored with the **User Story Solution Architect** (v1.10). Vertical: **Provider Network Management (PNM)**. Workflow mode: **Bug Fix**.
> **Component verification note:** the `code-review-graph` knowledge graph for this workspace is effectively empty (2 JavaScript file nodes, 0 edges, no Apex indexed), so it returned nothing for these components. Every class, method, field, record type, OmniScript, and Integration Procedure named below was verified by direct metadata inspection — exact file paths and line numbers are cited in **Current State**.
> **Closes an open question from another story:** `RCAT_RecredUpdates_PNC_LocationRepoint_UserStory.md` Clarification #1 asked whether the RCAT auto-batch PNC path should be re-pointed in a separate story. This is that story.

**Persona:** Credentialing Specialist
**Priority:** P0
**OmniScripts:** `PRM_ReviewRCAT_English` (active version 10 — **no field change**; note two versions are flagged active in source, v8 and v10 — reconcile before deploying), `PRM_PractitionerTerminationRecredForm_English` (active version 4 — **changed**: restrict the termination choice and fix its duplicate option label)
**Integration Procedures:** `PRM_ReviewRCAT_Procedure`, `PRM_ReviewRCATLoad_Procedure`, `PRM_ReviewRCATLoadParent_Procedure`, `PRM_UpdateDataForRCATPNCReview_Procedure` (**no change** — the guided flow already reads location-level PNC correctly)
**Apex (the actual change surface):** `PRM_RCATTerminationBatchHelper` (`pncOnlyPractitioner`, `delegatedOnlyPractitioner`, `processPractitioners`), `PRM_FutureDatedProcessingBatchHandler` (`processPractitioners`, `processPractitonersForL4`), `PRM_PractitionerPNCBatchHelper` (source of the canonical rule)
**Objects:** `Account` (Practitioner Person Account), `HealthcareFacility` (practice location), `HealthcarePractitionerFacility` (affiliation)
**Relevant Requirements:** `RCAT_RecredUpdates_PNC_LocationRepoint_UserStory.md` (Clarification #1), `PRM_PNC_AppReview_Flows_User_Stories.md` (US1 location PNC field, US4 rollup), `PRM_PNC_Logic_Change_Implementation_Plan.md`, `PRM_PNCAnyLocation_DataModel_User_Story.md` (manual PNC override), `PRM_PNC_PPL_DirectoryIndicator_User_Story.md` (downstream consumer), `PRM_PNC_CredentialingStatus_Blank_User_Story.md` (**overlapping owner of the blank-status rule — see Related User Stories**)

> **Third rule added to this story:** a practitioner associated to an **LMS (last-man-standing) location *plus* a Delegated or PNC location** reaches **RCAT Screen 2** (the Last Man Standing review), and the downstream **Recred Updates** termination must be **restricted to "Convert to Non-Participating" only** — a full termination is invalid for them because they still participate at their PNC/Delegated locations. Specified in **Added scope — RCAT Screen 2 hand-off** (AC-20 – AC-23). Verifying it surfaced a **live defect**: the active recred termination form shows **two options with the identical label "Convert to Non-Participating"**, one of which performs a full termination (AC-23).

> **Second rule added to this story:** a practitioner whose every active practice location is **PNC or Delegated** must be left with a **blank Credentialing Status and no Recred Due Date**. This is the same rule `PRM_PNC_CredentialingStatus_Blank_User_Story.md` already ratified for the PDA / creation / Override paths (and that `PRM_RecalculatePNCFlowAction` lines 46–50 already implements); this story extends it to the **three termination paths**, to **Delegated** practitioners, and to the **mixed PNC + Delegated** case that neither flag catches. Confirmed with the requester: blank **wins over `Terminated`** even on the non-participating branch, and the rule fires for any combination of PNC and Delegated locations.

---

## Story

**As a** Credentialing Specialist completing an RCAT (Recredentialing Committee Action Team) review,
**I want** a practitioner whose every remaining active practice location is PNC (Par Non Cred) to come out of the termination correctly flagged as PNC — and any practitioner left with only PNC or Delegated locations to carry no credentialing status and no recred due date,
**So that** the practitioner's participation, credentialing status, directory visibility, and recred obligations all reflect that they participate without full individual credentialing by us, without anyone having to fix the record by hand afterwards.

**Why it matters:** the PNC flag on the practitioner is the switch that drives downstream credentialing status blanking, participation status, directory suppression, and letter generation. Today, when RCAT terminates a practitioner whose only remaining locations are PNC, the flag is written as **not PNC** — the exact opposite of the truth. The Credentialing Specialist sees a practitioner who looks fully credentialed, so the practitioner keeps a credentialing status they should not have and stays eligible for member-facing directory publication. Because RCAT writes the flag on every run, it also silently overwrites whatever the nightly recalculation had correctly set, so the error keeps coming back and cannot be fixed by editing the record.

The credentialing-status and recred-due-date side of it compounds the same problem. A practitioner who is only PNC or Delegated is not credentialed by us, so a credentialing status of "Credentialed" or "Terminated" and a populated recred due date are both wrong — and they are not cosmetic: the recred due date is what pulls a practitioner into recred-due reporting, CAQH-due checks, due notifications, and recred case-manager creation. Leaving it populated means Credentialing keeps chasing recredentialing for practitioners who will never be recredentialed individually, and the specialist has no way to tell the real recred population from the noise.

---

## Scope

| Flow | Component | Affected Step | Data Source (where PNC is read) |
|------|-----------|---------------|---------------------------------|
| RCAT Review (guided flow) | `PRM_ReviewRCAT_English` v10 | PNC / Delegated review screens | Location PNC — **correct today**, no change |
| RCAT Review (load) | `PRM_RCATProcessingHelper.buildLocationsForPractitioners` | Builds each location row shown to the Specialist | `HealthcareFacility.PRM_PNC__c` on **`PRM_PractitionerLocationAffiliation`** records — **correct today** |
| RCAT termination (auto-batch) | `PRM_RCATNetworkTerminationBatch.finish` → `PRM_RCATTerminationBatchHelper.processPractitioners` | Writes the practitioner's PNC flag, credentialing status, and recred due date | `PRM_RCATTerminationBatchHelper.pncOnlyPractitioner` — **the defect** |
| Future-dated processing | `PRM_FutureDatedProcessingBatchHandler.processPractitonersForL4` / `processPractitioners` | Writes the practitioner's PNC flag + participation routing + credentialing status | Same defective helper, **plus** a separate vendor-level PNC read |
| Recred Updates termination | `PRM_FullPracTermRecredBatchService` | Calls the same shared `processPractitioners` | Same defective helper |
| Nightly recalculation (reference) | `PRM_PractitionerPNCBatchHelper` | Recalculates the practitioner PNC flag | `HealthcareFacility.PRM_PNC__c` on **`PRM_PractitionerLocationAffiliation`** records — **the canonical rule** |
| RCAT Review — screen routing | `PRM_RCATProcessingHelper.evalLocations` → `PRM_RCATProcessingService.bucketizeScreens` | Decides which of the three review screens a practitioner appears on | LMS candidacy + location PNC/Delegated — **correct today; the overlap flag needs surfacing** |
| Recred termination form | `PRM_PractitionerTerminationRecredForm_English` v4 | The `FullTermination` ("Full-Termination?") choice | **New restriction + duplicate-label defect** |

### Credentialing status / recred due date — added scope

| Object | Field | Applies to | Current behaviour | Required |
|---|---|---|---|---|
| Account (Practitioner) | `PRM_CredentialingStatus__c` | Every active location is PNC or Delegated | `''` on the Participating branch (only when decision date <= today); `Terminated` on the Non-Par branch | `''` (blank) unconditionally |
| Account (Practitioner) | `PRM_ReCredDueDate__c` | Every active location is PNC or Delegated | **Never written** by any termination path — a stale due date survives | `NULL` |

---

## Current State (from codebase)

### The defect — wrong affiliation record type

`PRM_RCATTerminationBatchHelper.pncOnlyPractitioner()` (`force-app/main/default/classes/PRM_RCATTerminationBatchHelper.cls`, lines 718–752) queries:

```
FROM HealthcarePractitionerFacility
WHERE RecordType.DeveloperName = 'PRM_PractitionerPracticeAffiliation'   // <-- practitioner-to-GROUP
  AND PractitionerId IN :practitionerIds
  AND IsActive = true
```

`PRM_PractitionerPracticeAffiliation` is the **practitioner-to-practice (group / practitioner-to-practitioner) affiliation** — confirmed by `PRM_GlobalConstant.RECTYPEID_PRACTITIONERPL` (line 52) being the record type used by `PRM_RCATTerminationBatchHelper.getHCPFPracToPrac` (line 310, the "PracToPrac" query). The **practice-location** affiliation is `PRM_PractitionerLocationAffiliation` (`PRM_GlobalConstant.RECTYPEID_PLAFFILIATION`, line 51).

Every other component that evaluates location PNC uses the **location** record type:

| Component | Record type used | File / line |
|---|---|---|
| `PRM_PractitionerPNCBatchHelper` (canonical nightly rollup) | `PRM_PractitionerLocationAffiliation` | `PRM_PractitionerPNCBatchHelper.cls` line 13, 84 |
| `PRM_RCATProcessingHelper` (what the guided flow shows) | `RECTYPEID_PLAFFILIATION` | `PRM_RCATProcessingHelper.cls` line 71 |
| `PRM_RCATTerminationBatchHelper.delegatedOnlyPractitioner` | `PRM_PractitionerLocationAffiliation` | same file, line 765 |
| `PRM_RCATTerminationBatchHelper.getActiveHCPFCountByPractitioner` | `PRM_PractitionerLocationAffiliation` | same file, line 332 |
| `pncOnlyPractitioner` | **`PRM_PractitionerPracticeAffiliation`** | same file, **line 729** |

**Failure mechanism:** the method seeds every practitioner to `true`, then flips to `false` on any non-PNC facility, and finally flips to `false` for any practitioner that matched **no rows** (lines 742–746). A practitioner whose active affiliations are all *practice-location* affiliations matches no rows in this query, so they fall into the "no records → false" branch. The result is written straight onto the account at `processPractitioners` line 832/846:

```
acc.PRM_PNC__c = pracPNC.containsKey(acc.PersonContactId) ? pracPNC.get(acc.PersonContactId) : false;
```

The guided flow does bucket these practitioners correctly — `PRM_RCATProcessingService.bucketizeScreens` (line 242) sets `pncCombined` from the locations, and `PRM_RCATNetworkTerminationBatch` (lines 34–36, 103–118) does call `processPractitioners` for them. So the entry path works; the value computed inside `pncOnlyPractitioner` is what is wrong.

### Three adjacent defects in the same code (all confirmed in scope)

1. **Vendor-level PNC read still in place.** `PRM_FutureDatedProcessingBatchHandler` lines 822–830 builds its PNC map from `hpf.Account.PRM_PNC__c` (the **vendor/group** account) on `PRM_PractitionerPracticeAffiliation` records. That map feeds `getpractitionerIdToPncOrDelegatedMap` (line 846) and drives participation-status routing in `processPractitonersForL4` (lines 938–949). It is the pre-migration group-PNC pattern that `PRM_PNC_Logic_Change_Implementation_Plan.md` moves to the location.
2. **Facility active state ignored.** `pncOnlyPractitioner` and `delegatedOnlyPractitioner` do not filter on `HealthcareFacility.PRM_Active__c` and do not exclude affiliations with no facility. `PRM_PractitionerPNCBatchHelper.getActiveFacilityPncMap` (line 114) does filter on `PRM_Active__c = true`, and its `getAccountToFacilityIds` (line 83) excludes `HealthcareFacilityId = null`. Consequence today: a null facility yields `null` for the PNC field, which is not `== false`, so the practitioner is left at the seeded `true` — the same method can therefore also set PNC *incorrectly true*.
3. **Manual PNC override ignored.** `PRM_PractitionerPNCBatchHelper.getPractitionerAccountsQueryLocator` (line 26) excludes `PRM_BypassPNC__c = true` accounts and filters to the `PRM_Practitioner` record type. The RCAT and future-dated writes apply neither guard, so RCAT overwrites a deliberately hand-managed PNC value.

### The canonical rule (to be reused, not re-invented)

`PRM_PractitionerPNCBatchHelper.isPncTrueForAllFacilities` (lines 129–144): **PNC is true only when the practitioner has at least one active practice location AND every one of those active locations is PNC** — otherwise false. This matches the intent of the name `pncOnlyPractitioner` and is the definition the fix must adopt.

### Downstream consumers of the flag (why P0)

`Account.PRM_PNC__c` (label *PNC*, Checkbox, history tracked) is read by `PRM_PNC_PPL_DirectoryIndicator_User_Story.md` (directory suppression), `PRM_PNC_CredentialingStatus_Blank_User_Story.md` (credentialing-status blanking), `PRM_PNCPDABatchHelper`, `PRM_RecalculatePNCFlowAction`, and `PRM_PractitionerPNCDailyBatchHelper`.

---

## Acceptance Criteria

**AC-1 — A practitioner whose every active practice location is PNC is flagged PNC (happy path)**

**Given** a Credentialing Specialist has completed an RCAT review for a practitioner whose every remaining active practice location is marked PNC,
**When** the RCAT termination finishes processing that practitioner,
**Then** the practitioner is flagged as PNC,
**And** the Credentialing Specialist sees the PNC indicator on the practitioner without having to set it by hand.

**AC-2 — A practitioner with a mix of PNC and non-PNC locations is not flagged PNC**

**Given** a practitioner has at least one active practice location that is not PNC alongside one or more that are PNC,
**When** the RCAT termination finishes processing that practitioner,
**Then** the practitioner is not flagged as PNC,
**And** the outcome is the same regardless of how many of the locations are PNC.

**AC-3 — A practitioner with no active practice locations is not flagged PNC (edge case)**

**Given** a practitioner has no remaining active practice locations after the RCAT termination,
**When** the RCAT termination finishes processing that practitioner,
**Then** the practitioner is not flagged as PNC.

**AC-4 — Group-level affiliations no longer decide the practitioner's PNC outcome (root cause)**

**Given** a practitioner whose every active practice location is PNC, and who has no affiliation recorded directly to a practitioner group,
**When** the RCAT termination finishes processing that practitioner,
**Then** the practitioner is still flagged as PNC,
**And** the presence or absence of a group-level affiliation makes no difference to the PNC outcome,
**And** the PNC outcome is decided only by the practitioner's own practice locations.

**AC-5 — Closed and inactive practice locations are ignored (edge case)**

**Given** a practitioner has one active practice location that is PNC and one closed or inactive practice location that is not PNC,
**When** the RCAT termination finishes processing that practitioner,
**Then** the practitioner is flagged as PNC,
**And** the closed or inactive location does not influence the outcome.

**AC-6 — The manual PNC override is respected (negative)**

**Given** a practitioner whose PNC flag is being managed by hand because the manual PNC override is switched on,
**When** the RCAT termination finishes processing that practitioner,
**Then** the practitioner's PNC flag is left exactly as the business set it,
**And** the RCAT termination does not overwrite it in either direction,
**And** every other field the termination writes is still updated as normal.

**AC-7 — RCAT and the nightly recalculation always agree**

**Given** a practitioner has just been processed by an RCAT termination,
**When** the nightly PNC recalculation runs against that same practitioner with no data changing in between,
**Then** the recalculation leaves the PNC flag unchanged,
**And** the two processes never produce opposite PNC values for the same practitioner.

**AC-8 — Future-dated processing decides PNC from the practitioner's own locations**

**Given** a future-dated termination becomes effective for a practitioner whose every active practice location is PNC, and whose group was historically flagged PNC,
**When** the future-dated processing runs,
**Then** the practitioner is flagged as PNC based on their own practice locations,
**And** the group's historical PNC flag no longer influences either the PNC flag or the participation outcome,
**And** a practitioner with a mix of PNC and non-PNC locations under a formerly-PNC group is not flagged PNC.

**AC-9 — Recred Updates termination produces the same PNC outcome**

**Given** a practitioner whose every active practice location is PNC is terminated through the Recred Updates flow instead of RCAT,
**When** the termination finishes,
**Then** the practitioner is flagged as PNC,
**And** the PNC outcome is identical to what the RCAT termination would have produced for the same practitioner.

**AC-10 — No regression to the rest of the termination**

**Given** an RCAT termination that ends a practitioner's participation,
**When** the termination runs,
**Then** the practitioner's participation status, effective dates, non-participating start date, termination reason, case manager, and error indicator are all set exactly as they are today,
**And** the practitioner's related records — affiliations, providers, taxonomy, NPI, identifiers, board certifications, info codes, and network participation — are terminated exactly as they are today,
**And** letter generation and the case manager's completion status are unaffected,
**And** for a practitioner who has at least one plain practice location (neither PNC nor Delegated), the credentialing status and recred due date also behave exactly as they do today — only the PNC-or-Delegated-only case changes them (AC-13, AC-16).

**AC-11 — A bulk RCAT decision completes without failure (scale)**

**Given** a Credentialing Specialist submits an RCAT decision covering a large number of practitioners, each with multiple practice locations,
**When** the termination runs,
**Then** every practitioner receives the correct PNC outcome,
**And** no practitioner is skipped or fails because of processing limits.

**AC-12 — Practitioners already mis-flagged by this defect are corrected (one-time)**

**Given** practitioners who were processed by an RCAT or future-dated termination before this fix and are recorded as not PNC even though every one of their active practice locations is PNC,
**When** the one-time correction is run,
**Then** each of those practitioners is flagged as PNC,
**And** any of those practitioners still carrying a credentialing status or a recred due date has both cleared,
**And** a record of exactly which practitioners changed and from what value is produced for Credentialing sign-off before the change is committed,
**And** practitioners whose locations do not all qualify are not modified,
**And** practitioners whose manual PNC override is switched on are not modified.

**AC-13 — A practitioner with no plain practice location carries no credentialing status and no recred due date (happy path)**

**Given** a practitioner who has at least one active practice location, and whose every active practice location is either PNC or Delegated,
**When** the termination finishes processing that practitioner,
**Then** the practitioner's credentialing status is blank,
**And** the practitioner's recred due date is cleared,
**And** a practitioner with **zero** active practice locations does not qualify — their credentialing status and recred due date follow today's behaviour, consistent with the zero-location rule for the PNC flag (AC-3),
**And** the same outcome applies whether the change came from the RCAT termination, future-dated processing, or the Recred Updates termination.

**AC-14 — Any mix of PNC and Delegated locations qualifies (edge case)**

**Given** a practitioner who has one active PNC practice location and one active Delegated practice location, and no other active practice location,
**When** the termination finishes processing that practitioner,
**Then** the practitioner's credentialing status is blank and their recred due date is cleared,
**And** this holds even though the practitioner is neither flagged PNC nor flagged Delegated Only, because neither flag is true for a mixed set,
**And** the two flags themselves are still set independently by their own all-locations rules.

**AC-15 — A non-participating PNC-or-Delegated practitioner is still left blank, not Terminated (edge case)**

**Given** a practitioner whose every active practice location is either PNC or Delegated, and who has no remaining active plan-based network participation,
**When** the termination finishes processing that practitioner,
**Then** the practitioner's credentialing status is blank rather than Terminated,
**And** the recred due date is cleared,
**And** the practitioner's participation status is still set to Non-Par exactly as it is today.

**AC-16 — A practitioner with at least one plain practice location keeps today's behaviour (negative)**

**Given** a practitioner who has at least one active practice location that is neither PNC nor Delegated,
**When** the termination finishes processing that practitioner,
**Then** the credentialing status is set exactly as it is today — blank when the practitioner stays participating, Terminated when they become non-participating,
**And** the recred due date is left untouched,
**And** none of this story's credentialing-status or recred-due-date changes apply to that practitioner.

---

### Pattern E — Record & Field Specification

The termination's practitioner write. The **PNC**, **Credentialing Status**, and **Recred Due Date** rows change as a result of this story; every other field is enumerated so the developer preserves it exactly and QA can assert the whole record.

Throughout these tables, **"PNC-or-Delegated only"** means: the practitioner has **at least one** active practice location **and every** active practice location is PNC or Delegated, in any combination (AC-13, AC-14).

**AC-17 — Records updated when the termination completes (outcome = Participating)**

**Given** a practitioner processed by the RCAT termination who still has active plan-based network participation,
**When** the RCAT termination finishes processing that practitioner,
**Then** the following record is updated exactly as specified:

**Practitioner Person Account — Update**

| Field | Value | Notes |
|---|---|---|
| PNC | `TRUE` when the practitioner has **at least one** active practice location **and every** active practice location is PNC; otherwise `FALSE` | **Changed by this story.** Not written at all when the Bypass PNC override is on (AC-6) |
| Delegated Only | `TRUE` when the practitioner has at least one active practice location and every active practice location is Delegated; otherwise `FALSE` | Existing behaviour; active-location guard added (AC-5) |
| Is Error Record | `TRUE` only when the practitioner has zero active practice locations **and** `{Decision Date}` < current Effective From; otherwise `FALSE` | Unchanged |
| Effective To | `NULL` when Is Error Record = `TRUE`; otherwise current Effective To | Unchanged |
| Effective From | `{TODAY}` when Is Error Record = `TRUE`; otherwise current Effective From | Unchanged |
| Active | `FALSE` when Is Error Record = `TRUE`; otherwise current Active | Unchanged |
| Case Manager | `{Case Manager of the RCAT decision}` | Unchanged — see Clarification #4 |
| Non-Participating Start Date | `NULL` | Unchanged |
| Participating Code | `Participating` | Unchanged |
| Credentialing Status | `''` (blank) when `{Decision Date}` <= `{TODAY}`; **also `''` (blank) unconditionally when PNC-or-Delegated only** | **Changed by this story** — the PNC-or-Delegated-only case no longer depends on the decision date (AC-13) |
| Recred Due Date | `NULL` when PNC-or-Delegated only; otherwise **not written** | **New in this story** (AC-13, AC-16) |
| Termination Reason | `{Termination Reason of the RCAT decision}` | Unchanged |

**AC-18 — Records updated when the termination completes (outcome = Non-Par)**

**Given** a practitioner processed by the RCAT termination who has no remaining active plan-based network participation,
**When** the RCAT termination finishes processing that practitioner,
**Then** the following record is updated exactly as specified:

**Practitioner Person Account — Update**

| Field | Value | Notes |
|---|---|---|
| PNC | `TRUE` when the practitioner has **at least one** active practice location **and every** active practice location is PNC; otherwise `FALSE` | **Changed by this story.** Not written at all when the Bypass PNC override is on (AC-6) |
| Delegated Only | `TRUE` when the practitioner has at least one active practice location and every active practice location is Delegated; otherwise `FALSE` | Existing behaviour; active-location guard added (AC-5) |
| Is Error Record | `TRUE` only when the practitioner has zero active practice locations **and** `{Decision Date}` < current Effective From; otherwise `FALSE` | Unchanged |
| Effective To | `NULL` when Is Error Record = `TRUE`; otherwise current Effective To | Unchanged |
| Effective From | `{TODAY}` when Is Error Record = `TRUE`; otherwise current Effective From | Unchanged |
| Active | `FALSE` when Is Error Record = `TRUE`; otherwise current Active | Unchanged |
| Case Manager | `{Case Manager of the RCAT decision}` | Unchanged — see Clarification #4 |
| Non-Participating Start Date | `{Decision Date}` | Unchanged |
| Participating Code | `Non-Par` | Unchanged |
| Credentialing Status | `''` (blank) when PNC-or-Delegated only; otherwise `Terminated` when `{Decision Date}` <= `{TODAY}` | **Changed by this story** — blank wins over `Terminated` for the PNC-or-Delegated-only case (AC-15) |
| Recred Due Date | `NULL` when PNC-or-Delegated only; otherwise **not written** | **New in this story** (AC-13, AC-15) |
| Termination Reason | `{Termination Reason of the RCAT decision}` | Unchanged |

**AC-19 — Records updated by the one-time correction**

**Given** the one-time correction identified practitioners mis-flagged by this defect,
**When** the correction is committed,
**Then** the following record is updated exactly as specified:

**Practitioner Person Account — Update**

| Field | Value | Notes |
|---|---|---|
| PNC | `TRUE` | Only for Practitioner-record-type accounts with Bypass PNC off, at least one active practice location, and every active practice location PNC |
| Credentialing Status | `''` (blank) | Only for Practitioner-record-type accounts with Bypass PNC off that are PNC-or-Delegated only and still carry a status |
| Recred Due Date | `NULL` | Same population as the Credentialing Status row above |

**Objects explicitly NOT written by this story**

| Object | Field | Reason |
|---|---|---|
| `HealthcareFacility` | `PRM_PNC__c` | Source of truth — read only |
| `HealthcarePractitionerFacility` | any | Affiliation termination is unchanged (AC-10) |
| `HealthcareFacilityNetwork` | any | Network termination is unchanged (AC-10) |
| `IndividualApplication` | any | Case manager completion is unchanged (AC-10) |
| `Account` (Vendor / Group) | `PRM_PNC__c` | Practitioner Person Accounts only |

---

### Added scope — RCAT Screen 2 hand-off: restrict Recred Updates to "Convert to Non-Participating"

**The requirement:** *if a practitioner is associated to an LMS location **plus** a Delegated or PNC group, they land on RCAT Screen 2, and Recred Updates should be restricted to "Convert to Non-Participating" only.*

**Why:** such a practitioner still participates at their PNC/Delegated locations, so a **full termination** is factually wrong — it would end a participation that legitimately continues. The only correct action is to convert them to non-participating at the location(s) being terminated. The RCAT PNC & Delegated screen already states this intent in its own on-screen warning: *"Practitioners will only be termed from their Non-Delegated or Non-PNC Locations."* This rule enforces the same guarantee for the practitioner who reaches the Last Man Standing screen instead.

**Verified routing (this is today's behaviour, not a change):** in the active `PRM_ReviewRCAT_English` **v10**, the three review screens run in this `sequenceNumber` order — **Screen 1** `ReviewPNCAndDelegated` ("Review PNC & Delegated", seq 3.0), **Screen 2** `ReviewLastManStanding` ("Review Last Man Standing", seq 4.0), **Screen 3** `ReviewNotLastANDPNCDelegated` ("Review RCAT", seq 7.0). `PRM_RCATProcessingHelper.evalLocations` (lines 185–203) sets `goesToList1` when **any** location is an LMS candidate (`countOfActivePrac == 1` **and** not PNC **and** not Delegated) and `goesToList2` when **any** location is PNC or Delegated. `PRM_RCATProcessingService.bucketizeScreens` then resolves the overlap with `if (goesToList1) … else if (goesToList2) …` — so **LMS wins**, and a practitioner with both kinds of location is placed on the LMS screen (Screen 2) and does **not** appear on the PNC & Delegated screen. That confirms the requirement's routing premise; the **new** behaviour is the restriction on the downstream action.

**Qualifying rule for the restriction:**

| Practitioner's active locations | Screen | Recred Updates choices |
|---|---|---|
| ≥1 LMS location **and** ≥1 PNC/Delegated location | Screen 2 (Last Man Standing) | **"Convert to Non-Participating" only** — new |
| ≥1 LMS location, **no** PNC/Delegated location | Screen 2 (Last Man Standing) | Both choices — unchanged |
| No LMS location, ≥1 PNC/Delegated location | Screen 1 (PNC & Delegated) | Unchanged — out of scope here |
| Neither | Screen 3 (Review RCAT) | Unchanged — out of scope here |

**AC-20 — A practitioner with both an LMS location and a PNC/Delegated location is reviewed on Screen 2 (precondition)**

**Given** a practitioner who has at least one active practice location where they are the only active practitioner and which is neither PNC nor Delegated,
**And** at least one other active practice location that is PNC or Delegated,
**When** the Credentialing Specialist opens the RCAT review,
**Then** that practitioner is presented on the Last Man Standing review screen,
**And** the practitioner is not also presented on the PNC & Delegated review screen,
**And** this restates today's routing — it is the precondition for AC-21, not a change.

**AC-21 — Recred Updates for that practitioner offers only "Convert to Non-Participating"**

**Given** a practitioner who qualifies under AC-20,
**When** the Recred Updates termination is opened for that practitioner,
**Then** "Convert to Non-Participating" is the only termination choice available,
**And** a full termination cannot be selected or submitted for that practitioner,
**And** the choice is pre-selected so the Specialist cannot leave it unanswered,
**And** the practitioner's participation at their PNC or Delegated locations is left intact.

**AC-22 — A practitioner with no PNC or Delegated location keeps both choices (negative)**

**Given** a practitioner on the Last Man Standing screen whose every active practice location is neither PNC nor Delegated,
**When** the Recred Updates termination is opened,
**Then** both the full-termination and "Convert to Non-Participating" choices remain available exactly as they are today,
**And** none of this restriction applies to that practitioner.

**AC-23 — The two termination choices are distinguishable (defect found while specifying this)**

**Given** a Credentialing or PDM Specialist viewing the termination-type choice on the recred termination form,
**When** the choices are displayed,
**Then** each choice carries a distinct, self-explanatory label,
**And** the choice that performs a **full termination** is not labelled "Convert to Non-Participating",
**And** the Specialist can tell from the labels alone which choice ends participation entirely.

> **Live defect this AC fixes:** in the active `PRM_PractitionerTerminationRecredForm_English` **v4**, the required `FullTermination` field (label *"Full-Termination?"*) has **two options with the identical display name** `Convert to Non-Participating` — one carrying the value `Full-Termination`, the other `Convert to Non-Participating` (lines 2699–2707). The Specialist therefore sees two choices that read the same, one of which silently performs a **full termination**. This must be resolved as part of the restriction work: relabel the full-termination option honestly, then hide/remove it for qualifying practitioners. Related: `SVTerminationTypeSelected` (line 4348) already hard-sets `FullTermination` to `Convert to Non-Participating`, and a downstream step is gated on that exact value (lines 4158–4160) — so the mechanism to enforce the restriction already exists and mainly needs a conditional.

---

## Technical Implementation (high-level)

| Component | Type | Change | Drives |
|---|---|---|---|
| `PRM_PractitionerPNCBatchHelper` | Modified Apex (helper) | Expose the canonical computation as a reusable, `static`, contact-keyed entry point (e.g. `getPncByPractitionerContactId(Set<Id>)`) wrapping the existing `getAccountToFacilityIds` → `getActiveFacilityPncMap` → `isPncTrueForAllFacilities` chain. Keep `getAccountsToUpdate` behaviour byte-identical so the nightly batch is untouched. This is the single definition both paths consume. | AC-1–AC-5, AC-7 |
| `PRM_RCATTerminationBatchHelper.pncOnlyPractitioner` | Modified Apex (defect fix) | Delegate to the canonical helper instead of its own SOQL. Removes the `PRM_PractitionerPracticeAffiliation` record-type filter (line 729), the unused `Account.PRM_PNC__c` field in the select (line 726), and the null-facility hole. Keep the `Map<Id, Boolean>` signature keyed by `PersonContactId` so callers are unchanged. | AC-1–AC-5, AC-7, AC-9 |
| `PRM_RCATTerminationBatchHelper.delegatedOnlyPractitioner` | Modified Apex | Add `HealthcareFacilityId != null` and `HealthcareFacility.PRM_Active__c = true` to the affiliation query for symmetry with the PNC rule; record type is already correct. | AC-5, AC-10 |
| `PRM_PractitionerPNCBatchHelper` — new derived condition | Modified Apex (helper) | Alongside the canonical PNC map, expose a **PNC-or-Delegated-only** map (e.g. `getNonCredentialedOnlyByPractitionerContactId(Set<Id>)`): `TRUE` when the practitioner has ≥1 active practice location and **every** active location has `PRM_PNC__c = true` **OR** `PRM_IsDelegated__c = true`. Add `PRM_IsDelegated__c` to `getActiveFacilityPncMap`'s select so one query serves all three computations. This is the single definition of the blank-status rule. | AC-13, AC-14, AC-15 |
| `PRM_RCATTerminationBatchHelper.processPractitioners` | Modified Apex | (a) Skip the `PRM_PNC__c` / `PRM_DelegatedOnly__c` assignments (lines 832–833, 846–847) when Bypass PNC is on; add `PRM_BypassPNC__c` and `PRM_ReCredDueDate__c` to `getPersonAccBasisContactId`'s select. (b) When the PNC-or-Delegated-only condition is true, set `PRM_CredentialingStatus__c = ''` in **both** branches — overriding the `'Terminated'` write at line 851 — and set `PRM_ReCredDueDate__c = null`. Leave both fields on today's logic otherwise. | AC-6, AC-13, AC-15, AC-16, AC-17, AC-18 |
| `PRM_FutureDatedProcessingBatchHandler` (~lines 822–830) | Modified Apex | Replace the vendor read `hpf.Account.PRM_PNC__c` on `PRM_PractitionerPracticeAffiliation` with the location-sourced PNC from the canonical helper, so `practitionerIdToPncOrDelegatedMap` (line 846) and the routing at lines 938–949 follow location PNC. | AC-8 |
| `PRM_FutureDatedProcessingBatchHandler.processPractitioners` (~lines 973–991) and `processPractitonersForL4` (~lines 938–949) | Modified Apex | Apply the same blank-status / cleared-recred-due-date rule. Today both set `'Terminated'` on the non-participating branch even when the practitioner is PNC or Delegated, and neither touches the recred due date. Note `processPractitioners` currently gates on `PRM_PNC__c \|\| PRM_DelegatedOnly__c`, which misses the mixed case — switch it to the new derived condition. | AC-13, AC-14, AC-15 |
| `PRM_FullPracTermRecredBatchService` (line 223) | Verify only | Consumes the shared `processPractitioners`; inherits both the PNC fix and the blank-status rule. Confirm no local PNC map shadows it, and that its own `'Terminated'` write (~line 72) does not re-stamp a PNC-or-Delegated-only practitioner after the shared write. Coordinate with `RCAT_RecredUpdates_PNC_LocationRepoint_UserStory.md`. | AC-9, AC-13 |
| `PRM_RCATPNCBackfillExecutor` (new) | New Apex (`PRM_IDataFixExecutor`) | One-time correction over Practitioner-record-type Accounts with `PRM_BypassPNC__c = false`: set `PRM_PNC__c = true` where the canonical rule yields `true` but the field is `false`, and blank `PRM_CredentialingStatus__c` + null `PRM_ReCredDueDate__c` where the PNC-or-Delegated-only condition holds but either field is populated. Registered as a `PRM_DataFixConfiguration__mdt` row and run via `PRM_DataFixScheduler.runNow()`; checks `PRM_DataFixContext.isDebugMode` to skip DML on the dry run, respects the row's record threshold, and emits the framework's old/new CSV. | AC-12, AC-19 |
| `PRM_RCATProcessingControllerTest` | Modified test | Cover: all-locations-PNC, all-Delegated, mixed PNC+Delegated, one-plain-location, zero-active-location, group-affiliation-absent, inactive-facility, null-facility, Bypass-PNC-on, Participating and Non-Par branches, and bulk (200). Assert `Account.PRM_PNC__c`, `PRM_CredentialingStatus__c`, and `PRM_ReCredDueDate__c` explicitly — the current suite asserts none of them. | AC-1–AC-7, AC-11, AC-13–AC-16 |
| `PRM_FutureDatedProcBatchHandlerTest` | Modified test | Add the formerly-PNC-group / non-PNC-location case for the re-pointed routing, plus the blank-status and cleared-recred-due-date assertions on both branches. | AC-8, AC-13, AC-15 |
| `PRM_PractitionerPNCBatchTest` | Modified test | Assert the extracted canonical entry point returns the same values as `getAccountsToUpdate` for the same data, and cover the new PNC-or-Delegated-only condition incl. the mixed case. | AC-7, AC-14 |
| `PRM_RCATProcessingHelper.evalLocations` / `LocationEval` | Modified Apex | Add a flag carrying **"has an LMS location AND has a PNC/Delegated location"** (`goesToList1 && goesToList2`, already computed — just not surfaced). Expose it on the screen payload so the downstream form can act on it without recomputing. No change to the existing bucketing precedence. | AC-20, AC-21 |
| `PRM_RCATProcessingService.RCATScreen` | Modified Apex | Carry the new flag through to the OmniScript payload alongside `pncCombined` / `delegatedCombined`, so Screen 2's rows expose it. | AC-20, AC-21 |
| `PRM_PractitionerTerminationRecredForm_English` (active **v4**) | Modified OmniScript | (a) **Relabel** the `FullTermination` option whose value is `Full-Termination` so it no longer reads `Convert to Non-Participating` (lines 2699–2707). (b) Add a conditional so that, for a qualifying practitioner, only the `Convert to Non-Participating` option renders and it is pre-selected — reusing the existing `SVTerminationTypeSelected` set-values step (line 4348) rather than adding a new mechanism. Bump to a new version; do not edit v4 in place. | AC-21, AC-22, AC-23 |
| `PRM_ReviewRCAT_English` — **source hygiene blocker** | Verify / clean | Source currently has **two versions marked `isActive=true`** (v8 and v10). Ground all work against **v10** and reconcile the stale flag before touching the script, or the wrong version may be retrieved/deployed. See `OmniScript_StaleActiveVersions_SourceHygiene_UserStory.md`. | AC-20 |
| Recred termination form tests / flow regression | New + modified tests | Cover: qualifying practitioner sees one choice; non-qualifying sees both; full termination cannot be submitted for a qualifying practitioner; PNC/Delegated locations survive the conversion. | AC-21, AC-22, AC-23 |

**Notes for the developer:**

- **Record type names are the trap.** `PRM_GlobalConstant.RECTYPEID_PRACTITIONERPL` resolves to `PRM_PractitionerPracticeAffiliation` (group) and `RECTYPEID_PLAFFILIATION` resolves to `PRM_PractitionerLocationAffiliation` (practice location) — the constant names read backwards from what they hold. Use the developer names, and resolve them through cached describe, not SOQL on `RecordType`.
- **Key on the right Id.** `pncOnlyPractitioner` is keyed by `PersonContactId` (the practitioner Contact), while `PRM_PractitionerPNCBatchHelper` works from `Practitioner.AccountId`. The extracted entry point must accept contact Ids and return contact-keyed results, or every caller breaks silently.
- **"No locations" must stay false.** The seed-`true`-then-flip-`false` shape is what makes the current bug silent. Prefer computing from the location set directly (as `isPncTrueForAllFacilities` does) so an empty set is unambiguously `false`.
- `pncOnlyPractitioner` and `delegatedOnlyPractitioner` currently swallow exceptions into `PRM_ExceptionLogger` and return a partially-populated map, which lets a failure write `false` onto real accounts. Preserve the logging but skip the PNC write when the computation did not complete.
- Reuse `PRM_ExceptionLogger.logException(...)`; keep the queries bulk-safe and outside loops — this runs inside `finish()` alongside two chained batch invocations.
- The write goes through `PRM_AccountTrigger`, so the directory-suppression rule from `PRM_PNC_PPL_DirectoryIndicator_User_Story.md` will fire on the corrected value. That is intended; regression-test the two together.
- **The blank-status rule is a third condition, not either flag.** `PRM_PNC__c` and `PRM_DelegatedOnly__c` are both all-or-nothing per type, so a practitioner with one PNC location and one Delegated location has **both flags false** while still qualifying for blank status (AC-14). Do not gate the blank write on `PRM_PNC__c || PRM_DelegatedOnly__c` — that is exactly the bug `PRM_FutureDatedProcessingBatchHandler.processPractitioners` (line 976) has today.
- **Pick the delegation source deliberately.** Two definitions exist (Clarification #8): the facility checkbox `HealthcareFacility.PRM_IsDelegated__c` (what the batch flags use) versus an active Delegation info code on the facility (what the guided flow shows the Specialist). The spec above assumes the checkbox. Do not mix them, and do not assume they agree.
- **Blank means blank.** `PRM_CredentialingStatus__c` is a restricted picklist whose valid values are `Credentialing In Progress`, `Credentialed`, `Denied`, `Terminated`, and empty. The existing code writes `''`; keep that convention rather than switching to `null` so the two paths stay comparable in tests and field history.
- **Precedent to follow, not re-invent.** `PRM_RecalculatePNCFlowAction` (lines 46–50) already sets `PRM_ReCredDueDate__c = null, PRM_CredentialingStatus__c = null` together when a practitioner is forced into PNC, and `PRM_PNC_CredentialingStatus_Blank_User_Story.md` ratified that rule for the PDA, creation, and override paths. This story extends the same rule to the termination paths and to Delegated — align the semantics with that story rather than inventing a second variant.
- **The "LMS + PNC/Delegated" flag already exists — it is just discarded.** `evalLocations` computes both `goesToList1` and `goesToList2`, and `bucketizeScreens` then throws away the fact that both were true when it picks the LMS branch. Surface that overlap rather than re-deriving it from the location list in a second place.
- **Two OmniScripts are plausibly "Recred Updates" — pick deliberately.** `PRM_ReCredUpdate_English` (active v7, label *"Recred Update"*) has **no** termination-type choice at all; the `Convert to Non-Participating` option lives only in `PRM_PractitionerTerminationRecredForm_English` (active v4). The spec above targets the latter. Confirm before building (Clarification #13).
- **Recred due date is destructive.** Clearing `PRM_ReCredDueDate__c` removes the practitioner from recred-due reporting and recred case-manager creation (`PRM_RecredDuePractitionersReportBatch`, `PRM_CheckCAQHAccessOnDueAccountsBatch`, `PRM_UpdateCaseManagerBatch`). The field is history-tracked, which is what makes the 30-day restore in the override story possible — do not disable that tracking.

---

## Definition of done

- [ ] An RCAT termination of a practitioner whose every active practice location is PNC leaves the practitioner flagged PNC (AC-1) — verified in QA on a real case.
- [ ] Mixed-location and zero-location practitioners come out not PNC (AC-2, AC-3).
- [ ] A practitioner with no group-level affiliation still resolves correctly (AC-4) — this is the regression test for the defect.
- [ ] Inactive/closed locations and affiliations with no location are excluded (AC-5).
- [ ] Bypass PNC accounts are never overwritten by the termination (AC-6).
- [ ] Running the nightly recalculation immediately after an RCAT termination produces zero changes (AC-7) — the consistency proof.
- [ ] Future-dated processing no longer reads group-level PNC; no `Account.PRM_PNC__c` read remains in `PRM_FutureDatedProcessingBatchHandler` (AC-8) — grep clean.
- [ ] Recred Updates termination yields the same PNC outcome as RCAT for the same practitioner (AC-9).
- [ ] Full field-by-field parity on the practitioner write for both Participating and Non-Par outcomes; only PNC, Credentialing Status, and Recred Due Date differ from pre-fix behaviour (AC-10, AC-17, AC-18).
- [ ] A practitioner whose every active location is PNC or Delegated comes out with a blank credentialing status and no recred due date, on both the Participating and Non-Par branches (AC-13, AC-15) — verified in QA.
- [ ] The mixed one-PNC-plus-one-Delegated practitioner qualifies for blank status even though neither flag is true (AC-14) — this is the case a naive `PNC || Delegated Only` check misses.
- [ ] A practitioner with at least one plain location still gets today's credentialing status and keeps their recred due date (AC-16).
- [ ] The same three outcomes hold for future-dated processing and Recred Updates termination, not just RCAT (AC-13).
- [ ] Recred-due reporting, CAQH-due checks, and recred case-manager creation confirmed to exclude the newly-blanked practitioners, with no error raised by a blank status on a participating practitioner.
- [ ] Bulk RCAT decision of 200+ practitioners completes with correct outcomes and no limit failures (AC-11).
- [ ] Backfill run in dry-run mode first, CSV reviewed and signed off by Credentialing, then committed (AC-12, AC-19).
- [ ] `PRM_PractitionerPracticeAffiliation` no longer appears in any PNC computation — grep clean across `PRM_RCATTerminationBatchHelper` and `PRM_FutureDatedProcessingBatchHandler`.
- [ ] ≥85% Apex coverage on every changed class incl. bulk (200), single, zero-location, all-PNC, all-Delegated, mixed, one-plain-location, inactive-facility, null-facility, Bypass-PNC, and exception paths; real assertions on `Account.PRM_PNC__c`, `PRM_DelegatedOnly__c`, `PRM_CredentialingStatus__c`, and `PRM_ReCredDueDate__c`.
- [ ] Field history on `Account.PRM_PNC__c`, `PRM_CredentialingStatus__c`, and `PRM_ReCredDueDate__c` shows the corrected values for a QA-verified practitioner.
- [ ] A practitioner with an LMS location plus a PNC/Delegated location is confirmed to appear on the Last Man Standing screen and not the PNC & Delegated screen (AC-20).
- [ ] For that practitioner, the recred termination offers **only** "Convert to Non-Participating", pre-selected, and a full termination cannot be submitted (AC-21) — verified in QA on a real case.
- [ ] Their PNC/Delegated locations remain active after the conversion (AC-21).
- [ ] A practitioner with no PNC/Delegated location still sees both choices (AC-22).
- [ ] The duplicate `Convert to Non-Participating` option label is fixed so the two choices are distinguishable (AC-23).
- [ ] `PRM_ReviewRCAT_English` stale `isActive` flag reconciled (v8 vs v10) before any OmniScript change is deployed.
- [ ] New OmniScript version created rather than editing active v4 in place.
- [ ] No regression in `PRM_PractitionerPNCBatchTest`, `PRM_RCATProcessingControllerTest`, `PRM_FutureDatedProcBatchHandlerTest`, or the recred termination suite.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Confirm the business rule is **"every** active practice location is PNC" (matching the nightly rollup and the `pncOnlyPractitioner` name) and **not** "any location is PNC" — the guided flow's own PNC/Delegated bucketing uses *any*, so the two intentionally differ. | The core computation; changes AC-1/AC-2 outcomes | BA / Product |
| 2 | Should Delegated Only continue to be computed independently of PNC, and what is the intended outcome for a practitioner whose active locations are a mix of PNC-only and Delegated-only? | Whether both flags can be false for a fully non-standard practitioner | BA |
| 3 | For AC-6, should a Bypass PNC practitioner be skipped only for the PNC field, or should the whole practitioner write be skipped? Written today as PNC-and-Delegated-Only only. | Blast radius of the override guard | Technical / BA |
| 4 | Separate observation in the code being touched: `PRM_RCATNetworkTerminationBatch.finish` (lines 107–113) overwrites `caseMgrId` on each loop iteration, so in a multi-practitioner decision every practitioner receives the **last** screen's Case Manager. Fix here or raise separately? | Case Manager accuracy on bulk RCAT decisions | Technical / BA |
| 5 | How far back should the backfill reach — all practitioners currently mis-flagged, or only those touched by an RCAT/future-dated run since the defect shipped? | Backfill query scope and volume | Ops / Credentialing |
| 6 | Do any downstream extracts, letters, or outbound directory feeds cache the PNC flag such that a re-publish is needed after the backfill? | Cutover / refresh step | Technical / Integration |
| 7 | Should the RCAT path stop writing PNC entirely and instead chain `PRM_PractitionerPNCBatch` after termination (one owner for the flag), rather than sharing the computation? Current design shares the computation but keeps two writers. | Long-term ownership of the flag; affects AC-7 design | Technical / Architecture |
| 8 | **Two definitions of "Delegated location" exist and they disagree.** The RCAT guided flow marks a location delegated from an **active Delegation info code** on the facility (`PRM_RCATProcessingService.loadDelegationMap`, lines 191–207: `PRM_InfoCodeAssignment__c` where `PRM_InfoCode__r.PRM_Type__c = DELEGATION`), while `delegatedOnlyPractitioner` and the future-dated handler read the **`HealthcareFacility.PRM_IsDelegated__c` checkbox**. Which definition governs the new blank-status rule? Written today as the checkbox, to match the flags it sits beside. | Which practitioners qualify for blank status; could change the outcome for any facility where the two disagree | BA / Technical |
| 8a | **"Any" vs "all" mismatch, same surface.** The guided flow routes a practitioner into the PNC/Delegated bucket when **any** location is PNC or Delegated (`evalLocations` → `anyPnc` / `anyDelegated`, `PRM_RCATProcessingService` lines 294–297), and that bucket is what feeds the termination batch. The flags and this story's blank rule use **all**. So a practitioner with one PNC location and one plain location is shown to the Specialist as PNC/Delegated but is correctly *not* flagged PNC and correctly keeps their credentialing status. Confirm that divergence is intentional (the screen is a review prompt, the flag is the outcome) rather than a second bug. | If "any" is the intended rule for blank status too, AC-13/AC-16 invert for mixed practitioners | BA / Product |
| 9 | Should a Delegated practitioner really carry a blank credentialing status? PNC means "participating, not credentialed by us", which clearly implies blank — but a Delegated practitioner *is* credentialed, just by the delegate. Confirm the business wants both treated identically. | Whether AC-13 covers Delegated at all | BA / Product |
| 10 | Is clearing the recred due date acceptable as a **destructive** change, or should the prior value be recoverable (the override story restores it from field history within 30 days)? The termination path has no equivalent restore today. | Whether a restore path is needed when a practitioner later gains a plain location | BA / Ops |
| 11 | Does any report, list view, or validation treat a **blank** credentialing status on a *participating* practitioner as an error? The existing PNC story raised the same question (its CQ #6) and it is still open. | Hidden downstream breakage | BA / Ops |
| 12 | When a PNC-or-Delegated-only practitioner later gains a plain practice location, should the credentialing status and recred due date be re-established, and by which process? Out of scope here. | Whether a follow-up story is needed | BA |
| 13 | **Which flow is "Recred Updates"?** `PRM_ReCredUpdate_English` (active v7, labelled *"Recred Update"*) has no termination-type choice; the `Convert to Non-Participating` option exists only in `PRM_PractitionerTerminationRecredForm_English` (active v4). AC-21 targets the latter. Confirm. | Which OmniScript is modified; wrong pick means the restriction is unenforceable | BA / Technical |
| 14 | **Is "Screen 2" the Last Man Standing screen?** By `sequenceNumber` in active v10 the order is PNC & Delegated (3.0), Last Man Standing (4.0), Review RCAT (7.0), so Screen 2 = Last Man Standing — which matches the requirement, since an LMS + PNC/Delegated practitioner is routed to the LMS bucket today. Confirm the Specialist counts the screens the same way. | If "Screen 2" means a different screen, AC-20 and the routing premise change | BA |
| 15 | Should the restriction apply when **any** location is PNC/Delegated (as written), or only when the PNC/Delegated location belongs to a **group/vendor** specifically? The requirement says "Delegated or PNC **Group**", but the RCAT evaluation is per **practice location**, and there is no group-level PNC read left after the migration. Written as per-location. | Which practitioners get restricted | BA |
| 16 | Should selecting the restricted option be **enforced server-side** as well, or is hiding the option in the form sufficient? A UI-only restriction can be bypassed by a direct IP/API call. | Whether server-side validation is needed | Technical / Security |
| 17 | For a qualifying practitioner, should the full-termination option be **hidden** or **shown-but-disabled with an explanation**? Hidden is written; disabled-with-reason is often better for training and audit. | UX and Specialist comprehension | BA / UX |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_RCATTerminationBatchHelper` | Apex (helper) | HIGH | Contains the defective `pncOnlyPractitioner` and the account write |
| `PRM_PractitionerPNCBatchHelper` | Apex (helper) | HIGH | Canonical rule extracted for reuse; nightly batch must stay behaviour-identical |
| `PRM_FutureDatedProcessingBatchHandler` | Apex (batch handler) | HIGH | Second caller of the defective helper, plus its own group-level PNC read driving participation routing |
| `PRM_RCATNetworkTerminationBatch` | Apex (batch) | MEDIUM | Invokes the account write in `finish()`; also carries the Case Manager observation (Clarification #4) |
| `PRM_FullPracTermRecredBatchService` | Apex (service) | MEDIUM | Shares `processPractitioners`; inherits the fix — coordinate with the Recred re-point story |
| `PRM_RCATPNCBackfillExecutor` | Apex (data fix, new) | MEDIUM | One-time correction of already-mis-flagged practitioners |
| `Account.PRM_PNC__c` | Field | HIGH | Value corrected; drives directory suppression, credentialing status, and participation downstream |
| `Account.PRM_DelegatedOnly__c` | Field | MEDIUM | Active-location guard added to its computation |
| `Account.PRM_CredentialingStatus__c` | Field | HIGH | Now blanked for PNC-or-Delegated-only practitioners on both branches, overriding the `Terminated` write |
| `Account.PRM_ReCredDueDate__c` | Field | HIGH | Now cleared for PNC-or-Delegated-only practitioners — newly written by these paths |
| `PRM_RecredDuePractitionersReportBatch`, `PRM_CheckCAQHAccessOnDueAccountsBatch`, `PRM_UpdateCaseManagerBatch`, `PRM_RecredCAQHDueNotifyBatchHandler`, `PRM_RecredSendEmailOnDueHandler` | Apex (recred-due consumers) | HIGH | All key off `PRM_ReCredDueDate__c` and/or `PRM_CredentialingStatus__c`; blanking both silently removes these practitioners from recred processing — the intended outcome, but it must be confirmed, not assumed |
| `PRM_PNCPDABatchHelper` | Apex | MEDIUM | Owns the same blank-both rule for the PDA path (`PRM_PNC_CredentialingStatus_Blank_User_Story.md`); keep the semantics identical |
| `PRM_RecalculatePNCFlowAction` | Apex | MEDIUM | Already blanks both on forced PNC (lines 46–50); the precedent this rule must match, plus the 30-day restore that reverses it |
| `PRM_ReviewRCAT_English` v10 / `PRM_ReviewRCAT_Procedure` | OmniScript / IP | LOW | No PNC change — already location-sourced; regression only. **But source has two `isActive=true` versions (v8, v10)** — reconcile before deploying |
| `PRM_RCATProcessingHelper.evalLocations` / `PRM_RCATProcessingService.RCATScreen` | Apex | MEDIUM | Must surface the already-computed LMS + PNC/Delegated overlap on the screen payload; bucketing precedence unchanged |
| `PRM_PractitionerTerminationRecredForm_English` v4 | OmniScript | HIGH | Restricts the termination choice for qualifying practitioners **and** fixes the duplicate-label defect on the `FullTermination` field |
| `PRM_PractitionerPNCDailyBatchHelper` | Apex (other PNC writer) | LOW | Unchanged, but must no longer disagree with RCAT (AC-7) |
| Directory-suppression and credentialing-status-blanking rules | Apex (downstream) | MEDIUM | Will now fire on the corrected flag — regression-test together |
| `PRM_RCATProcessingControllerTest`, `PRM_FutureDatedProcBatchHandlerTest`, `PRM_PractitionerPNCBatchTest` | Apex tests | HIGH | Need new assertions; the current suites do not assert the PNC flag |

---

## Estimated Effort (AI-estimated — validate with team)

| Component | Change Type | Effort | Notes |
|-----------|-------------|--------|-------|
| `PRM_PractitionerPNCBatchHelper` — extract canonical entry point | Apex (refactor) | M | Contact-keyed overload; nightly batch must stay identical |
| `PRM_RCATTerminationBatchHelper.pncOnlyPractitioner` — delegate to canonical | Apex (defect fix) | M | Removes the wrong record type, unused select field, and null-facility hole |
| `PRM_RCATTerminationBatchHelper.delegatedOnlyPractitioner` — active-location guard | Apex | S | Query filter only |
| `processPractitioners` — Bypass PNC guard | Apex | M | Needs the override field added to the account query |
| `PRM_PractitionerPNCBatchHelper` — new PNC-or-Delegated-only condition | Apex | M | Third derived map; add the delegated field to the existing facility query so it stays one SOQL |
| Blank credentialing status + clear recred due date across the three termination paths | Apex | L | Four write sites (`PRM_RCATTerminationBatchHelper` ×2 branches, future-dated `processPractitioners` and `processPractitonersForL4`); must override the existing `Terminated` write |
| `PRM_FutureDatedProcessingBatchHandler` — re-point vendor PNC read | Apex | L | Changes participation routing; needs its own regression pass |
| `PRM_RCATPNCBackfillExecutor` | Apex (new data-fix executor) | L | Dry-run CSV, threshold, override exclusion; now corrects three fields rather than one |
| `PRM_DataFixConfiguration__mdt` row | Config | S | One row registering the backfill executor |
| Unit tests across three suites | Apex tests | XL | Bulk 200, all-PNC, all-Delegated, mixed, one-plain-location, zero-location, inactive/null facility, Bypass PNC, both branches, exception path; real assertions on all four fields |
| Recred-due consumer regression (recred report, CAQH due, recred CM creation, due notifications) | QA | M | Confirms the blanked practitioners drop out cleanly and nothing errors on a blank status |
| Surface the LMS + PNC/Delegated overlap on the RCAT screen payload | Apex | S–M | Flag already computed in `evalLocations`; just needs exposing |
| Restrict the recred termination choice + fix the duplicate option label | OmniScript (new version) | M | Conditional render + pre-select; reuses the existing set-values step |
| Server-side enforcement of the restriction (if required per Clarification #16) | Apex / IP | M | Only if UI-only is judged insufficient |
| `PRM_ReviewRCAT_English` stale active-version cleanup | Source hygiene | S | Prerequisite, not optional |
| Recred termination restriction tests + flow regression | Tests / QA | M | Qualifying vs non-qualifying, submit-blocking, PNC/Delegated locations survive |
| Shadow parity / QA regression (RCAT + future-dated + recred, plus directory-suppression interaction) | QA | L | Both branches, multi-location practitioners |

**Total Estimated Effort:** **XL** (≈18 story points) — the PNC fix itself is small and surgical; the cost is in the four credentialing-status write sites, the three test suites, the future-dated routing re-point, the recred-consumer regression, and the OmniScript restriction with its label defect.

> **Recommended split:** this story now carries three separable concerns — (1) the PNC record-type defect + adjacent fixes, (2) the blank-status / cleared-recred-due-date rule, (3) the Screen 2 → Recred Updates restriction. Concern (3) touches a different layer (OmniScript, not Apex batch) with a different persona and its own defect, and has five open clarifications. If the sprint needs smaller units, split (3) out first — nothing in (1) or (2) depends on it.

---

## Related User Stories

- `RCAT_RecredUpdates_PNC_LocationRepoint_UserStory.md` — **directly related.** Its Clarification #1 asks whether the RCAT auto-batch PNC path should be a separate story; this story is the answer. Both touch the recred termination surface, so sequence them together to avoid a merge conflict in `PRM_FullPracTermRecredBatchService`.
- `PRM_PNC_AppReview_Flows_User_Stories.md` — US1 (`HealthcareFacility.PRM_PNC__c` exists) and US4 (the practitioner rollup). **This story depends on both** and does not change either.
- `PRM_PNCAnyLocation_DataModel_User_Story.md` — the manual PNC override that AC-6 must respect.
- `PRM_PNC_PPL_DirectoryIndicator_User_Story.md` — downstream consumer of the corrected flag; regression-test alongside.
- `PRM_PNC_CredentialingStatus_Blank_User_Story.md` — **overlapping owner of the blank-status rule.** That story owns "PNC → blank Credentialing Status + blank Recred Due Date" for the **PDA, practitioner-creation, and Override/Bypass** paths, including the 30-day restore on revert. **This story owns the same rule for the three termination paths and extends it to Delegated and to the mixed PNC+Delegated case** (AC-13 – AC-16). Neither story should redefine the rule — if the business changes it, change both. Sequence this one after that story's PDA change so the semantics land together, and reuse whatever shared helper it produces.
- `PRM_BypassPNC_UpdateFlow_User_Story.md` — implements the Override on/off blanking and the 30-day restore of Credentialing Status + Recred Due Date. Relevant here because a practitioner blanked by this story's termination path could later be restored by that flow; confirm the two do not fight (Clarification #10).
- `PRM_PNC_Logic_Change_Implementation_Plan.md` — the parent group-to-location PNC migration this defect is a residue of.
- `RCAT_PracticeLocation_NonPar_FullTerm_Batch_UserStory.md` — sibling RCAT batch behaviour; **overlaps AC-21** since it also governs full-termination vs non-par outcomes for RCAT-terminated practitioners. Review the two together so the restriction and that story's batch behaviour agree.
- `OmniScript_StaleActiveVersions_SourceHygiene_UserStory.md` — **prerequisite for AC-20/AC-21.** `PRM_ReviewRCAT_English` has two versions flagged active in source (v8 and v10); resolve before touching either OmniScript.
