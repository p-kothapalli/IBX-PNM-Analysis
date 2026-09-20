# Future-Dated Termination — Push-Out & Post-Termination Edits

## User Story: Allow users to extend (push out) a future-dated termination and edit billing/mailing on a future-terminated Practice Location

Document Version: 1.0
Created: 2026-05-11
Created By: Product / Engineering Deep Dive
Epic: Provider Network Lifecycle — Termination & Re-Termination
Priority: P0 — Production data-integrity defect
Estimated Effort: L (1.5–2 sprints, see breakdown at bottom)
Vertical: Provider Network Management (PNM) — Independence Blue Cross (IBX)

---

## 1. Executive Summary

Two related production defects are reported by Credentialing / PDM users:

1. **"Push-out" of a future-dated termination is silently ignored.**
   If an Account (Vendor or Practitioner), Practice Location, Network, NPI,
   etc. is already terminated effective 2/1/2026 and a user re-runs the
   Termination guided flow with the date pushed to 3/1/2026, the system accepts
   the submission but the underlying records (and the
   `PRM_FutureDatedProcessing__c` staging rows on every child object) **stay on
   the earlier 2/1/2026 date**. The Future-Dated batch then terminates the
   record on the original (now-stale) date.

2. **Billing/Mailing address updates on a Practice Location with a future-dated
   termination are blocked or produce inconsistent data.**
   A user terminates a Practice Location effective 10/1/2026. Until 10/1/2026
   the location is still active and the billing/mailing address may need to
   change (e.g., remittance address change requested by the Practice). The
   Edit Billing/Mailing guided flow either errors, silently no-ops, or leaves
   the chain of Address records in an inconsistent state (old billing keeps
   `PRM_EffectiveTo__c = 10/1/2026 + PRM_Active__c = false`, new billing
   created open-ended with `PRM_EffectiveTo__c = null`, which never gets
   terminated on 10/1/2026).

Both defects share **the same root cause**: a "monotonic pull-in only" pattern
is hard-coded across ~12 termination helper classes and 1 OmniScript that
treats the earliest date as the canonical termination date and refuses to ever
extend it.

---

## 2. Architecture & Components Affected

### 2.1 The Future-Dated Processing pipeline

| Component | Role |
|-----------|------|
| `PRM_FutureDatedProcessing__c` (custom object) | Staging table — one row per record that will be activated/terminated on a future date. External Id = `{recordId}_{Activate\|Terminate}`. |
| `PRM_FutureDatedProcessingUtil.createRecords()` | Called from every relevant trigger (Account, HealthcareFacility, HealthcareFacilityNetwork, Address, Location, HealthcarePractitionerFacility, BoardCertification, HealthcareProviderNpi, Identifier, PRM_InfoCodeAssignment__c, PRM_ProgramParticipation__c, PRM_HealthcareFacilityAssociation__c, PRM_HealthcareFacilityBundleAssociation__c, PRM_HealthcareFacilityNPI__c, PRM_ContractHierarchy__c, PRM_ProviderFeature__c, PRM_HealthcareFacilityBundle__c, PRM_AccountContractEntity__c, HealthcareProvider, HealthcareProviderTaxonomy). Upserts FDP staging rows on the External Id, so a single record always has **one** open Terminate FDP and **one** open Activate FDP. |
| `PRM_FutureDatedProcBatchSchTermination` (Schedulable) | Fires daily; enqueues the batch with `status = "Terminate"` and `effDate = TODAY`. |
| `PRM_FutureDatedProcBatchSchActivation` (Schedulable) | Fires daily; enqueues the batch with `status = "Activate"` and `effDate = TODAY`. |
| `PRM_FutureDatedProcessingBatch` (Database.Batchable) | Picks FDP rows where `Processed = FALSE AND EffectiveDate = TODAY AND Status matches` and applies them to the target sObject (`EffectiveTo`, `Active`, `Status`, `NonParticipatingStartDate`, etc.). |
| `PRM_FutureDatedProcessingBatchHandler.deleteRedundentRecords()` | Cleans up duplicate FDP rows for the SAME sObject — but **only when EffectiveDate ≤ TODAY**. Duplicate / superseded FUTURE-dated rows are not cleaned up by this batch. |

### 2.2 The Termination guided flows

| Guided Flow / Component | Backing Apex |
|------------------------|--------------|
| `PRM_AccountTerminationForm_English_*` (OmniScript) | `PRM_AccountTerminationUtility` → `PRM_AccountTerminationBatch` → `PRM_AccountTerminationBatchHelper` |
| `PRM_PracticeLocationTermination_English_*` (OmniScript) | `PRM_PracticeLocationTermination_Procedure_*` (IP) → `PRM_TerminatePracticeLocationNRelations` → `PRM_CrossRefBatchHelper.terminateFacilityAndRelations()` |
| PDM Manual Update (`PRM_PDMManualUpdatePractitioner_*`) | `PRM_ManualUpdatePracLocTerminationBatch` → `PRM_PracLocTermHelper` |
| RCAT Termination (post-recred) | `PRM_RCATTerminationBatchHelper`, `PRM_RCATLocationTerminationBatch`, `PRM_RCATNetworkTerminationBatch`, `PRM_RCATTerminationEffectivityHelper` |
| Initial Cred Termination | `PRM_AccountTerminationInitialCredBatch`, `PRM_AccountTerminationInitialCredUtility`, `PRM_PractitionerTermInitialCredBatch`, `PRM_AccountTermInitalCredService` |
| Full Practitioner Termination | `PRM_FullPractitionerTerminationBatch` → `PRM_PractitionerTerminationBatchHelper.setTermDataPractitioner()` |
| Full Practice Termination (Recred) | `PRM_FullPracTerminationRecredBatch`, `PRM_FullPracTermForFacilityRecredBatch`, `PRM_FullPracTermForFacilityBatch` |
| Provider Change Termination | `PRM_ProvChangeTerminationBatch` |
| Address Edit (Billing/Mailing) | `prmAddrBillMailPrim` (LWC) + `PRM_AddrBillMailController` (Apex) + `PRM_AddressTriggerHandler` / `PRM_AddressTriggerHelper` |

---

## 3. Root-Cause Analysis

### 3.1 Defect #1 — Push-out is silently ignored

Across all "termination helper" classes, every related-record date update uses
one of two equivalent forms of a **monotonic pull-in-only** expression:

**Form A — `>=` guard (used on the Parent record)**
```apex
record.PRM_EffectiveTo__c = record.PRM_IsErrorRecord__c
    ? NULL
    : (record.PRM_EffectiveTo__c == NULL
        || record.PRM_EffectiveTo__c >= newTermDate)
       ? newTermDate
       : record.PRM_EffectiveTo__c;
```

**Form B — `< newTermDate` guard (used on Child records)**
```apex
record.EffectiveTo = record.EffectiveFrom >= newTermDate
    ? NULL
    : (record.EffectiveTo != null && record.EffectiveTo < newTermDate
        ? record.EffectiveTo
        : newTermDate);
```

Both rules say: *"If a child/related record already has an EARLIER
termination date, leave it alone."* This rule is **correct** when an unrelated
parent's termination is being applied as a cascade to children — you don't
want to extend a record that already independently terminates earlier. But
the SAME rule is applied when the user is **explicitly re-running the
termination flow on the parent to change the date**. In that case the
intent is "use my new date as the single source of truth for this whole
termination event" — but the code refuses to extend.

### 3.2 Confirmed occurrences

The pattern is duplicated in (file, line excerpts):

- `PRM_AccountTerminationBatchHelper.cls`
  - L16  `transformAccountData` (Account/Vendor)
  - L31  `transformAccountDataForNonPar`
  - L47  `getHcProvider`
  - L68  `getIdentifier`
  - L88  `getHcFacility`
  - L99  `transformFacilityData` (Practice Location)
  - L112 `transformLocationData` (Schema.Location)
  - L131 `getAddressData` (Schema.Address)
  - L150 / L168 `getIFCForVendor` / `getIFCForPracLoc`
  - L181 `getProgPartForVendor`
  - L228 / L245 `getHCFAssocData` / `getHCFBundleAssocData`
  - L258 `getHcPracFacForPracLoc`
  - L276 `getProgPartForFacility`
  - L303 `getHcProviderNPI`
  - L339 `getProviderTaxonomy`
  - L382 `getHcProvider (practitioner)`
  - L399 `getPractitonerNPI`
  - L413 `getPractitionerIdentifier`
  - L427 `getBoardCertifications`
  - L441 `getPractitionerIFC`
  - L453 `getHCPractitionerFacility`
  - L469 `getNetworkDataForPractitioner`
  - L484 `getAdmittingPrivileges`
  - L500 `getPracProviderTaxonomy`
- `PRM_PractitionerTerminationBatchHelper.cls`
  - L526 `setTermDataPractitioner` (Account = Practitioner Full-Term)
- `PRM_CrossRefBatchHelper.cls` (Practice Location Termination cascade)
  - **SOQL query level** (L68, L133, L158, L189, L219, L249, L313, L368, L405, L432, L495) — `WHERE (PRM_EffectiveTo__c = NULL OR PRM_EffectiveTo__c > :effectiveToDate)` — records with EXISTING earlier dates are **never even selected** during a push-out.
  - **Update level** (L45, L77, L142, L167, L202, L227, L263, L341, L377, L385, L413, L443, L471, L504) — same pull-in guard.
- `PRM_PracLocTermHelper.cls` (PDM Manual Update) — L183, L201, L218, L235, L255, L309, L328, L373, L425, L442, L458, L476, L494.
- `PRM_ManualUpdatePracLocTerminationBatch.cls` — L212 (HCF), L219 (Location), L298, L305 (Non-Par branch).
- `PRM_PracticeLocationTermination_English_18.os-meta.xml` OmniScript expressions
  - L884 NPI `EffectiveTo`
  - L924 HealthcareFacility `PRM_EffectiveTo__c` (this one DOES override directly without guard — good)
  - L929 Location `PRM_EffectiveTo__c` (push-out guard)
- (Likely also) `PRM_RCATTerminationBatchHelper.cls`, `PRM_RCATTerminationEffectivityHelper.cls`, `PRM_FullPractitionerTerminationBatch.cls`, `PRM_AccountTermInitalCredService.cls`, `PRM_AccountTerminationInitialCredUtility.cls`, `PRM_PractitionerTermInitalCredService.cls`, `PRM_FullPracTermForFacilityBatch.cls`, `PRM_FullPracTermForFacilityRecredBatch.cls`, `PRM_ProvChangeTerminationBatch.cls` — same pattern (counts confirmed via grep, exact lines to audit during implementation).

### 3.3 What actually happens during push-out today

Scenario: Vendor Account is terminated effective 2/1/2026 (today is 2026-05-11).

User opens Account Termination guided flow and enters **3/1/2026**. The OmniScript
posts to `PRM_AccountTerminationUtility.AccountTerminationBatch` which spawns
`PRM_AccountTerminationBatch` with `accountTerminationDate = 3/1/2026`.

| Step | Existing State | Code Path | Result |
|------|---------------|-----------|--------|
| 1 | Account.PRM_EffectiveTo__c = 2/1/2026 | `transformAccountData` L16 | `2/1/2026 >= 3/1/2026` is FALSE → keeps 2/1/2026. **No update on Account.** |
| 2 | Practice Location.PRM_EffectiveTo__c = 2/1/2026 | `transformFacilityData` L99 | Same — stays 2/1/2026. |
| 3 | Address.PRM_EffectiveTo__c = 2/1/2026 | `getAddressData` L131 | Same — stays 2/1/2026. |
| 4 | HCFN.EffectiveTo = 2/1/2026 | `getNetworkDataForPractitioner` L469 | Same. |
| 5 | All other child records | Same pattern. | Same — all stay 2/1/2026. |
| 6 | FDP staging records | Never re-upserted because triggers didn't fire (no field changes). | **All FDP rows still say 2/1/2026 + Status=Terminate.** |
| 7 | UI feedback | OmniScript runs to completion; bell notification "Termination complete." | **User believes push-out succeeded.** |
| 8 | 2/1/2026 hits | `PRM_FutureDatedProcessingBatch` fires for TODAY. | All FDP rows for 2/1/2026 are picked → records get terminated on the ORIGINAL date, not the date the user just set. |

The push-out is silently swallowed at every layer.

### 3.4 Defect #2 — Edit Billing/Mailing on a future-terminated Practice Location

Scenario: Practice Location terminated 10/1/2026 (well in the future); today
is 5/11/2026. User wants to update the Billing address (e.g., new
remittance address).

Trace:

1. Termination cascade in `PRM_CrossRefBatchHelper.terminateFacilityAndRelations`
   set every Billing/Mailing `Schema.Address.PRM_EffectiveTo__c = 10/1/2026` and
   `PRM_Active__c = TRUE` (10/1/2026 is still in the future). A
   `PRM_FutureDatedProcessing__c` row was upserted per address with EffectiveDate
   = 10/1/2026, Status = Terminate.
2. User opens the Edit Billing/Mailing guided flow / address management LWC.
   The query in `PRM_AddrBillMailController.getAddressData` only filters on
   `PRM_Active__c = TRUE AND PRM_Pending__c = FALSE` — it does **not**
   acknowledge a future `PRM_EffectiveTo__c`. The user sees the billing as
   "editable".
3. User submits the new billing. The LWC inserts a new
   `Schema.Address` with `PRM_AddressType__c = "Billing"`, `PRM_Active__c =
   TRUE`, `PRM_EffectiveFrom__c = today`, `PRM_EffectiveTo__c = NULL`.
4. `PRM_AddressTriggerHelper.processActivatedAddressTypes` →
   `updateExistingAddress` (line 214):
   ```apex
   existingAddr.PRM_EffectiveTo__c =
       existingAddr.PRM_EffectiveTo__c != NULL
         ? existingAddr.PRM_EffectiveTo__c            // keeps 10/1/2026 ← wrong
         : matchedAddr[0].PRM_EffectiveFrom__c;       // would have set to today
   existingAddr.PRM_Active__c = false;
   ```
   The OLD billing now reads: `Active = false`, `EffectiveTo = 10/1/2026`.
   That is internally contradictory ("inactive but live until October"). The
   FDP row for the old billing still says "Terminate on 10/1/2026" — which
   is now redundant (the address is already inactive).
5. The NEW billing has `EffectiveTo = NULL`. `PRM_FutureDatedProcessingUtil.createRecords`
   does NOT create a Terminate FDP row for it (the trigger only does so when
   `effectiveTo != null && effectiveTo > todayDate`). The new billing is
   **open-ended on a Practice Location scheduled to terminate 10/1/2026**.
6. On 10/1/2026, the FDP batch:
   - Reads the (still-existing) Terminate FDP row for the old billing and
     "terminates" it — no-op (it's already inactive with EffectiveTo set).
   - Terminates the Practice Location, Location, HCF, HCFN, etc.
   - **Does NOT terminate the new billing** because no FDP row was ever
     written for it. The new billing remains `Active = true` on an inactive
     Practice Location.

This produces a downstream data-integrity problem (PI/PDM extracts will pick
up an active billing on a terminated PL), and explains why the user feels
"it is causing problems today."

In some flows there is **also** a hard validation failure when the new
billing's `PRM_EffectiveFrom__c > Location.PRM_EffectiveTo__c` (e.g., user
enters a future EffectiveFrom past the termination date). The user-facing
error is generic and unhelpful.

### 3.5 Why pulling in works but pushing out doesn't

The "monotonic pull-in only" rule was originally designed for the case where
**a parent termination is cascading down to a child** and the child should
keep its independently-set earlier date. That makes sense in isolation. The
defect is that the same rule is reused when the **user is the source of
truth** — re-running the guided flow with a new date is supposed to overwrite
the previous date for that whole termination event. There is currently no way
to distinguish these two intents at the helper level.

---

## 4. Acceptance Criteria

### 4.1 Push-Out / Pull-In via Termination Guided Flow

Given a user is re-running ANY termination guided flow (Account, Practice
Location, Practitioner, RCAT, PDM Manual Update, Provider Change, Initial Cred,
Full Practitioner / Full Practice / Full Practice-Recred) on a record that
already has a future-dated `PRM_EffectiveTo__c` (or `EffectiveTo` /
`PRM_NonParticipatingStartDate__c` for non-par):

| # | Scenario | Existing Date | New Date | Expected Result |
|---|----------|--------------|----------|-----------------|
| AC1.1 | Pull in | 5/1/2026 | 3/1/2026 | All affected records re-stamped to 3/1/2026. FDP rows re-upserted to 3/1/2026 (or deleted if record already terminated). (Today's behavior — must continue to work.) |
| AC1.2 | Push out | 2/1/2026 | 3/1/2026 | All affected records re-stamped to 3/1/2026. FDP rows re-upserted to 3/1/2026. **The original 2/1/2026 FDP rows must NOT fire on 2/1/2026.** |
| AC1.3 | Same date | 2/1/2026 | 2/1/2026 | No-op, no errors. |
| AC1.4 | Past date (≤ today) | 2/1/2026 (future) | 2026-05-11 (today) | Apply immediately — record becomes inactive today; FDP rows deleted (no longer needed). Validate `EffectiveFrom ≤ new date`. |
| AC1.5 | Earlier than EffectiveFrom | 5/1/2025 EffFrom | 1/1/2025 | Block with explicit validation error: "Termination date cannot be earlier than the record's Effective From date (5/1/2025)." |
| AC1.6 | Push out beyond a child's independently-set termination | Account = 2/1/2026, an Identifier already has EffectiveTo = 4/1/2026 (set independently before the term flow ever ran) | Account pushed to 3/1/2026 | The Account, Practice Location(s), Addresses, HCF, HCFN, IFC, Program Participation, HCFAssoc, HCFBundleAssoc, HCPF, etc. that were aligned to 2/1/2026 must move to 3/1/2026. **The Identifier whose 4/1/2026 was independently set must remain at 4/1/2026** (still earlier than 3/1/2026? No, 4/1/2026 > 3/1/2026 — see AC1.7). |
| AC1.7 | Push out PAST an independent child date | Account = 2/1/2026, Identifier = 4/1/2026 (independent) | Account pushed to 5/1/2026 | Identifier termination date is **less restrictive** than the parent's — must stay at 4/1/2026 (don't overwrite a child that legitimately terminates earlier). Account moves to 5/1/2026. UI must surface a warning summarizing children that were not extended. |
| AC1.8 | Push out from "Convert to Non-Par" to a later non-par start date | NonParticipatingStartDate = 2/1/2026 | 3/1/2026 | Updated on Account and all children that pivot on this date. |
| AC1.9 | Switch termination type during push-out | Existing Convert-to-Non-Par 2/1/2026 | Full-Termination 3/1/2026 | Allowed. New cascade applies Full-Termination rules effective 3/1/2026; non-par fields cleared on the parent. |
| AC1.10 | Concurrent submission | User A submits 3/1/2026, User B submits 4/1/2026 within seconds | Last-write-wins (FDP upserted by ExternalId guarantees a single open FDP row). Both users see "Termination updated" — no DML lock errors. |

### 4.2 Future-Dated Processing batch correctness

| # | Scenario | Expected |
|---|----------|----------|
| AC2.1 | FDP row re-upserted to a later date (push out) | `PRM_FutureDatedProcessingUtil.createRecords` upserts by external id `{recordId}_Terminate` — only ONE Terminate FDP exists per record, always with the latest committed date. |
| AC2.2 | FDP scheduler runs on the old date after a push-out | No row picked up (the FDP for that record now has the new date; the old row has been replaced by the upsert). |
| AC2.3 | Cancel / Reverse a future-dated termination | User-action TBD: a "Cancel Future Termination" action sets `PRM_EffectiveTo__c = null` on the parent AND deletes/marks-processed the FDP rows for the parent and all children. Out of scope for this story unless explicitly added (see § 6 Out of Scope). |
| AC2.4 | Push-out across the FDP run window | If user pushes out at 11:59pm on 2/1/2026 (the day the FDP batch runs at 1:00am 2/2/2026), the new FDP record is already in place — the next-day batch won't pick the old date. ✔ via External-Id upsert. |
| AC2.5 | `deleteRedundentRecords` does not delete needed future FDP rows | Confirm: function only deletes FDP rows with `EffectiveDate ≤ TODAY` keeping `MAX(Id)`. After fix, no additional change required. |

### 4.3 Edit Billing / Mailing Address on a future-terminated Practice Location

| # | Scenario | Expected |
|---|----------|----------|
| AC3.1 | PL terminated on 10/1/2026, today is 5/11/2026, user opens Edit Address | UI shows a banner: "This Practice Location is scheduled to terminate on 10/1/2026. Address changes will apply until that date." Edit is **allowed**. |
| AC3.2 | User submits new Billing with no EffectiveTo | New Billing is auto-stamped `PRM_EffectiveTo__c = parentLocation.PRM_EffectiveTo__c` (10/1/2026). FDP staging row for the new Billing is created with EffectiveDate = 10/1/2026, Status = Terminate. New billing terminates alongside the PL. |
| AC3.3 | User submits new Billing with explicit EffectiveTo > Location.PRM_EffectiveTo__c | Block with explicit validation: "Billing address cannot extend beyond the Practice Location's termination date (10/1/2026)." |
| AC3.4 | User submits new Billing with explicit EffectiveFrom > Location.PRM_EffectiveTo__c | Block with explicit validation: "Billing address effective date cannot be after the Practice Location termination date (10/1/2026)." |
| AC3.5 | Old Billing closeout | `PRM_AddressTriggerHelper.updateExistingAddress` is fixed: old Billing gets `PRM_EffectiveTo__c = new Billing.PRM_EffectiveFrom__c - 1 day` (or same day, per business confirmation), `PRM_Active__c = false`, `PRM_IsErrorRecord__c = false`. This supersedes the previously-set 10/1/2026 termination date for the OLD address (the old address no longer needs to be "terminated" on 10/1/2026; it is already closed earlier). FDP row for the old Billing is updated (or deleted) so the FDP batch does not act on it again. |
| AC3.6 | PL termination is later cancelled (Reinstate) | Both the old and new Billing addresses must be reconciled — the new Billing's auto-stamped EffectiveTo should be cleared. Out of scope for this story but flagged as a downstream consideration. |
| AC3.7 | Same rules apply to Mailing | Edit Mailing follows the same pattern as Billing. |
| AC3.8 | Same rules apply to phone & alternative contact methods | `PRM_ContactMethod__c` records inherit the parent PL's EffectiveTo when added on a future-terminated PL. |

### 4.4 UX / Guardrails

| # | Scenario | Expected |
|---|----------|----------|
| AC4.1 | Termination guided flow lands on an already-terminated future-dated record | Show a banner / read-only summary: "This {Account / Practice Location / Practitioner} is scheduled to terminate on {existing date}. Submitting this flow with a different date will update the termination date." Pre-fill the `EffectiveTo` field with the existing date. |
| AC4.2 | Termination Reason change without date change | Allowed — reason updated, dates untouched, FDP rows untouched. |
| AC4.3 | Audit trail | A `PRM_AsyncProcess__c` (sub-type "FDTermination") row is already written by the FDP batch; ALSO write a one-line entry on the parent Case (`PRM_CaseDataManager__c`) recording `OldTerminationDate`, `NewTerminationDate`, and `ChangedBy` whenever the date is changed by a guided flow re-run. |
| AC4.4 | Bell notification copy | When date is changed (not first-time set), notification title: "Termination Date Updated — {Account / PL Name}". Body includes both old and new dates. |
| AC4.5 | OmniScript validation message | If user pushes earlier than EffectiveFrom or submits any of the AC3.x blocked scenarios, the OmniScript surfaces the precise field-level error inline; do not allow Submit. |

---

## 5. Design / Implementation Approach

### 5.1 Centralize the date computation

Create one utility method to replace the duplicated `(existing != null && existing < newTermDate)` pattern across all helpers:

```apex
public class PRM_TerminationDateUtility {
    public enum Mode {
        // The cascade is being driven by the user re-running the
        // termination guided flow on the parent. The new date is the
        // authoritative termination date for this whole event.
        USER_RE_TERMINATION,
        // The cascade is from a parent's auto-termination (e.g., LMS,
        // last-active-PL closes the practitioner). Honor children's
        // independently-set earlier dates.
        PARENT_CASCADE
    }

    public static Date computeEffectiveTo(
            Date existing,
            Date requested,
            Date effectiveFrom,
            Boolean isErrorRecord,
            Mode mode) {
        if (isErrorRecord) return null;
        if (effectiveFrom != null && effectiveFrom > requested) return null;
        if (existing == null) return requested;
        if (mode == Mode.USER_RE_TERMINATION) {
            // Always honor the user's submitted date.
            return requested;
        }
        // Parent cascade: keep the earlier of the two.
        return existing < requested ? existing : requested;
    }
}
```

Refactor each of the helper classes listed in § 3.2 to call this utility,
passing `Mode.USER_RE_TERMINATION` for all guided-flow entry points. For
`PARENT_CASCADE` paths (e.g., LMS auto-trigger on a child when last-active
sibling terminates), pass `Mode.PARENT_CASCADE`.

### 5.2 Fix `PRM_CrossRefBatchHelper` SOQL filters

Currently every cascade SELECT in `PRM_CrossRefBatchHelper` has
`AND (PRM_EffectiveTo__c = NULL OR PRM_EffectiveTo__c > :effectiveToDate)`,
which silently filters out push-out candidates. For
`Mode.USER_RE_TERMINATION` paths we need to remove this filter (or relax to
`(PRM_EffectiveTo__c = NULL OR PRM_EffectiveTo__c >= :originalEffectiveToDate)`)
so that records previously aligned to the old date are picked up and re-stamped
with the new date. Strategy:

1. Pass the *previous* `PRM_EffectiveTo__c` of the parent into
   `terminateFacilityAndRelations` alongside the new `effectiveToDate`.
2. For each child SELECT, broaden the filter to also include records whose
   `EffectiveTo` equals the previous parent date (those are records the
   previous cascade had aligned to the parent — they should be re-aligned to
   the new date).
3. Records whose `EffectiveTo` is OTHER than null, the old parent date, or
   > new parent date stay untouched (those are independently-set dates per
   AC1.7).

### 5.3 Address Trigger fix (`PRM_AddressTriggerHelper.updateExistingAddress`)

Change line 216 to use the new address's EffectiveFrom regardless of the
existing EffectiveTo (or business-confirmed offset; default = same day):

```apex
public static Schema.Address updateExistingAddress(
        Schema.Address existingAddr,
        Map<Id, List<Schema.Address>> filteredUpdatedRecords) {
    List<Schema.Address> matchedAddr = filteredUpdatedRecords.get(existingAddr.ParentId);
    Date newEffectiveFrom = matchedAddr[0].PRM_EffectiveFrom__c;
    // Always close the old address on the day the new one starts —
    // regardless of any future-dated termination already stamped on it
    // by a previous parent-cascade.
    existingAddr.PRM_EffectiveTo__c = newEffectiveFrom;
    existingAddr.PRM_Active__c = false;
    return existingAddr;
}
```

### 5.4 Address auto-inheritance on a future-terminated parent

In `PRM_AddressTriggerHandler.beforeInsert` / `beforeUpdate`, for any Address
being inserted/updated on a `Location` whose related `HealthcareFacility` has a
future-dated `PRM_EffectiveTo__c`, auto-stamp the new Address's
`PRM_EffectiveTo__c` to `MIN(submittedEffectiveTo, parent.PRM_EffectiveTo__c)`.

Same logic for `PRM_ContactMethod__c`, `Schema.Location`, and any other
child whose termination should be bounded by the parent's.

### 5.5 OmniScript / Guided Flow updates

#### `PRM_AccountTerminationForm_English_*`
- Pre-fill the `EffectiveTo` field with the existing `Account.PRM_EffectiveTo__c`
  via a DataRaptor on entry (currently null).
- Add a TextBlock visible when `Account.PRM_EffectiveTo__c != null`:
  "This Account is scheduled to terminate on {existing date}. Submitting will
  update the termination date."

#### `PRM_PracticeLocationTermination_English_*`
- Same pre-fill for `TerminateEffectiveTo` from
  `HealthcareFacility.PRM_EffectiveTo__c`.
- Same banner.
- Update the cascading expressions (lines 884, 929 in version 18) to call the
  new utility via a remote method, or simply remove the guard since the user
  is the authoritative source.

#### Edit Billing/Mailing (Address Management)
- Add a banner in `prmAddressGroupManager` / `prmAddrBillMailPrim` and the
  corresponding edit OmniScript: "This Practice Location is scheduled to
  terminate on {date}. Address changes will apply until that date."
- Pass `parentLocation.PRM_EffectiveTo__c` as `maxDate` to the date pickers
  for `PRM_EffectiveFrom__c` and `PRM_EffectiveTo__c` on the address form.

### 5.6 Batch and Scheduler considerations

No new batch is required. We are reusing
`PRM_FutureDatedProcBatchSchTermination` /
`PRM_FutureDatedProcessingBatch`. The fix relies on the External-Id upsert
in `PRM_FutureDatedProcessingUtil.createRecords` — it already guarantees
a single open FDP row per `{recordId}_Terminate`, so push-outs naturally
update the same FDP row.

Recommended **defensive cleanup**: extend
`PRM_FutureDatedProcessingBatchHandler.deleteRedundentRecords` to also delete
duplicate **future** FDP rows for the same `(PRM_SObjectRecordId__c,
PRM_Status__c)` keeping `MAX(Id)` — currently it only de-dupes for
`EffectiveDate ≤ TODAY`. This protects against any DML path that inserts
without going through the External-Id upsert (e.g., direct seed data, manual
fixes).

### 5.7 Backfill / Data Repair

A one-time data fix is needed for current production records where a previous
push-out attempt was silently swallowed:

1. Query `PRM_FutureDatedProcessing__c WHERE PRM_Status__c IN ('Terminate', 'Terminate - Last Man Standing') AND PRM_EffectiveDate__c >= TODAY AND PRM_Processed__c = FALSE`.
2. For each FDP, compare the FDP's EffectiveDate to the target sObject's
   current `PRM_EffectiveTo__c`. If they differ, write a one-time corrective
   FDP record using the **target sObject's** current date (since the sObject
   may have been correctly updated by some paths but not others).
3. Notify Credentialing leads of any rows that show a mismatch between the
   parent Account/Practice Location and any of its children (these may be
   the production cases the user is seeing today).

Estimate: 1 DataFix scheduler class (`DFX_FutureDatedTerminationDateRepair`)
extending `DFX_DataFixScheduler` pattern in the codebase.

---

## 6. Out of Scope (call out for follow-up stories)

1. **Cancel a future-dated termination** (set `PRM_EffectiveTo__c = NULL`)
   — there is no first-class "Undo Termination" guided flow today; only the
   `PRM_PracticeLocationReinstate_English_*` OmniScript supports reinstating
   an already-terminated PL. A clean "Cancel pending Termination before it
   fires" flow is its own user story.
2. **Reinstate-then-reapply chained edits** — if Cancel is added later, the
   address auto-inheritance logic in § 5.4 must be reversible.
3. **CAQH / PI extract impact** — push-out implications for any outbound
   roster files (CAQH, PI Dataset, PDM, BCBSA sync) are tracked separately.
   The FDP batch is the canonical source of "when does this terminate" — once
   the FDP row is correct, downstream extracts pick up the correct date.
4. **Validation rule centralization** — today's per-object EffectiveDate
   validation rules (`PRM_EffectiveDateValidation`) on
   `PRM_HealthcareFacilityAssociation__c`, `PRM_ContactMethod__c`,
   `PRM_HealthcareFacilityNPI__c`, etc. compare against the parent's
   EffectiveTo. They will start firing correctly once the parent's EffectiveTo
   moves; that is the expected behavior, but UAT should confirm no
   false-positive failures.

---

## 7. Affected Use Cases — Test Matrix

Every row below is a discrete UAT case for QA.

| # | Object Re-Terminated | Direction | Termination Type | Has Independent Child Dates | Through Which Flow |
|---|----------------------|-----------|------------------|------------------------------|--------------------|
| TC-01 | Account (Vendor) | Push out | Full | No | `PRM_AccountTerminationForm` |
| TC-02 | Account (Vendor) | Push out | Convert to Non-Par | No | `PRM_AccountTerminationForm` |
| TC-03 | Account (Vendor) | Pull in | Full | No | `PRM_AccountTerminationForm` (regression) |
| TC-04 | Account (Practitioner) | Push out | Full | No | `PRM_AccountTerminationForm` |
| TC-05 | Account (Practitioner) | Push out | Convert to Non-Par | No | `PRM_AccountTerminationForm` |
| TC-06 | Account (Practitioner, Initial Cred) | Push out | Full | No | `PRM_AccountTerminationInitialCredBatch` path |
| TC-07 | Practice Location | Push out | Full-Termination | No | `PRM_PracticeLocationTermination_English_*` |
| TC-08 | Practice Location | Push out | Convert to Non-Par | No | `PRM_PracticeLocationTermination_English_*` |
| TC-09 | Practice Location | Push out, LMS branch | Full | n/a | LMS auto-cascade (`PRM_PPLLMSTermService`) — verify cascade still respects original logic and does NOT use USER_RE_TERMINATION mode |
| TC-10 | Practice Location | Push out | Full | Yes (one Identifier with later independent date) | Verify child stays at its independent date; warning surfaced |
| TC-11 | Practice Location | Push out | Full | Yes (one Address with earlier independent date) | Verify Address moved to new date if it was aligned to the old PL date; stays if independently set earlier |
| TC-12 | Practice Location | Push from EffectiveTo IS NULL to a new future date | New termination | n/a | First-time set — must continue to work |
| TC-13 | Practitioner (Full Term) | Push out | Full | No | `PRM_FullPractitionerTerminationBatch` path |
| TC-14 | Practitioner (RCAT) | Push out | RCAT | No | `PRM_RCATTerminationBatchHelper` path |
| TC-15 | Practice Location (PDM Manual Update) | Push out | Par + Non-Par branches | No | `PRM_PDMManualUpdatePractitioner` → `PRM_ManualUpdatePracLocTerminationBatch` |
| TC-16 | Network (HCFN) | Push out | Standalone Network term | No | `PRM_RCATNetworkTerminationBatch` |
| TC-17 | Cross-Ref Practice Locations | Push out | Cross-Ref batch | No | `PRM_TerminatePracticeLocationNRelations` → `PRM_CrossRefBatchHelper` |
| TC-18 | Billing Address on future-terminated PL | New address with no EffectiveTo | n/a | n/a | Edit Address guided flow — verify auto-stamp |
| TC-19 | Mailing Address on future-terminated PL | New address with explicit EffectiveTo > PL term | Validation expected | n/a | Edit Address guided flow — verify validation error |
| TC-20 | Phone (ContactMethod) on future-terminated PL | Update phone | n/a | n/a | Verify auto-stamp |
| TC-21 | Batch run on the day a push-out was made | n/a | n/a | n/a | Push out from 2/1 to 3/1 on 2/1 at 11:59pm; verify FDP scheduler at 1am 2/2 does not terminate the record |
| TC-22 | Audit trail | n/a | Full | n/a | Verify `PRM_AsyncProcess__c` and case-level audit captured |
| TC-23 | Concurrent push-outs | Two users push out same Account at the same time | n/a | n/a | Verify last-write-wins, single FDP row, no locking error |
| TC-24 | Data Repair | One-time | n/a | Mixed | Run `DFX_FutureDatedTerminationDateRepair`, verify discrepant FDP rows realigned |
| TC-25 | LWC banner | UI test | n/a | n/a | Verify banner appears on guided flow entry when record has future EffectiveTo |
| TC-26 | Bell notification copy | UI test | n/a | n/a | Verify "Termination Date Updated" notification |

---

## 8. Estimated Effort

| Component | Size | Notes |
|-----------|------|-------|
| `PRM_TerminationDateUtility` new class + tests | S | 50–100 lines, well-covered by unit tests. |
| Refactor of `PRM_AccountTerminationBatchHelper` to use utility | M | 28 SOQL helpers, mostly mechanical. |
| Refactor of `PRM_PractitionerTerminationBatchHelper` (`setTermDataPractitioner`) | S | Single method. |
| Refactor of `PRM_CrossRefBatchHelper` (queries + cascade math) | L | 14 SOQLs to widen filter + integrate utility. |
| Refactor of `PRM_PracLocTermHelper` | M | 13 helpers. |
| Refactor of `PRM_ManualUpdatePracLocTerminationBatch` execute() | S | Inline expressions. |
| Refactor of `PRM_RCATTerminationBatchHelper`, `PRM_RCATTerminationEffectivityHelper`, `PRM_FullPractitionerTerminationBatch`, `PRM_FullPracTermForFacilityBatch`, `PRM_FullPracTermForFacilityRecredBatch`, `PRM_FullPracTerminationRecredBatch`, `PRM_AccountTermInitalCredService`, `PRM_AccountTerminationInitialCredUtility`, `PRM_PractitionerTermInitalCredService`, `PRM_ProvChangeTerminationBatch` | M | Each is mostly the same patterns; group as one PR per family. |
| `PRM_AddressTriggerHelper.updateExistingAddress` fix | S | One-line behavioural change. |
| New Address auto-inheritance in `PRM_AddressTriggerHandler` (before-insert/update) | M | Touches Address, ContactMethod, Location, ProviderFeature similarly. |
| OmniScript pre-fill + banner on 3 termination flows + Edit Address flow | M | Mostly Vlocity Build-Pack updates; no Apex changes. |
| Audit-trail entry on `PRM_CaseDataManager__c` | S | One field + one DML. |
| `DFX_FutureDatedTerminationDateRepair` data fix scheduler | M | Reuses existing DFX pattern. |
| Test classes (`*Test.cls`) — push-out coverage | L | Add ~20 test methods spread across existing test classes. |
| QA / UAT effort | L | 26 test cases in § 7. |

**Total: L (1.5–2 sprints with one developer + one Vlocity OmniStudio developer + one QA).**

---

## 9. Risks

1. **Regression on intentional cascade-keep-earlier-date semantics.**
   `PARENT_CASCADE` mode must be retained for LMS auto-trigger flows (e.g.,
   `PRM_PPLLMSTermService`). Test TC-09 explicitly guards this.
2. **Validation rule chain reaction.**
   When the parent's EffectiveTo moves later, existing validation rules
   (e.g., `PRM_HealthcareFacilityAssociation__c.PRM_EffectiveDateValidation`)
   compare child to parent — they will now correctly evaluate to TRUE. UAT
   should sample children at risk of failing validation post-fix.
3. **CAQH / PI / PDM downstream rosters.**
   Once FDP rows realign, the next outbound extract will show the new dates.
   For records mid-flight (e.g., already extracted with the old date), align
   with the Roster Submission team to send a correction.
4. **Audit-trail noise.**
   The `PRM_CaseDataManager__c` write per re-termination adds rows. Confirm
   acceptable with PDM team.

---

## 10. Appendices

### Appendix A — Open Questions (for stakeholder review)

| # | Question | Owner | Default |
|---|----------|-------|---------|
| Q1 | When closing out an OLD billing address being replaced on a future-terminated PL, should the OLD address EffectiveTo be the day BEFORE the new address EffectiveFrom, or the same day? | Business Analyst | Same day (current code intent). |
| Q2 | Should the user be allowed to push out a termination to a date AFTER the related Recred Due Date / NPI Expiration / License Expiration? | Credentialing Compliance | Block (today's behavior on Recred re-cred chain). |
| Q3 | Independent child dates (AC1.7) — should the user be warned in-flow, or just see the summary on the Case page after? | UX | In-flow warning + summary on Case page. |
| Q4 | Cancel pending Termination flow (see § 6 #1) — included in this story or follow-up? | Product | Follow-up. |
| Q5 | LMS / Last-Man-Standing — confirm `PRM_PPLLMSTermService` uses `Mode.PARENT_CASCADE` only and never `USER_RE_TERMINATION`. | Engineering | Yes (confirmed via code review). |

### Appendix B — File / Line References

See § 3.2 for the full enumeration of every line that uses the buggy
pattern. Use that list as the dev's working checklist during implementation.

