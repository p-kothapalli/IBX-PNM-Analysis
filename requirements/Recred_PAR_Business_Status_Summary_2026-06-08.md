# Recredentialing & PAR Form — Business Status Summary

**Date:** June 8, 2026
**Audience:** Business / Operations leadership
**Purpose:** A plain-language summary of where the Recredentialing PDA guided flow, the PSV "add a practice location" process, and the PAR form stand today — what is working, what is still being built, and what is currently broken — so the team can decide whether to resume the paused processes.

---

## The short answer

**We should not resume the paused Recredentialing PSV "add a location" process or the guided location changes yet.** The specific problems that caused us to pause — and several related data-accuracy problems — are understood and have solutions designed, but **the fixes are not yet live**. Resuming today would re-expose providers and members to the same errors (timeouts, wrong terminations, missing-data errors).

We can keep handling exceptions by email until the must-fix items below are deployed and verified.

---

## 1. What is built and working today

These capabilities exist and are in use:

- **The core Recredentialing guided review flows.** Specialists can work recred cases through application review, primary source verification (PSV), and QC. These screens are live and actively maintained.
- **The PAR (Practitioner Add Request) form.** Providers/locations can be submitted and processed through the standard PAR form for low-volume, straightforward cases.
- **A behind-the-scenes "case association" foundation.** We built the plumbing that ties each record created on a case back to that case, so that later edits by other teams don't silently break the case. The **record-creation half is in place and connected** to the PAR and PSV flows.
- **Concierge Medicine tracking — the back-end.** The data model, the automatic "is this a concierge provider" roll-up, and the supporting fields are built. (The on-screen concierge questions on the forms are not yet live — see Outstanding.)
- **A terminated-location warning banner.** When a specialist opens a provider whose location has been terminated, a red warning now appears on the record so they are alerted before they start. (This warns only — it does not correct the underlying data.)
- **Low-volume location processing.** For providers with a small number of practice locations, the existing process behaves as it always has.

> Important: "built" means the software exists in our codebase. Before relying on any of it in production, we still need to confirm the correct version is switched on in the live environment.

---

## 2. What is outstanding (designed but not yet built/live)

These are planned and specified, but **not yet delivered**:

| # | Outstanding item | Why it matters |
|---|------------------|----------------|
| 1 | **High-volume location processing for the PSV route** | This is the #1 reason we paused. Providers with 100+ locations time out today. The fix (process locations in the background) is designed but **not built**. Until then, high-volume PSV add-location is not safe. |
| 2 | **"Read" side of the case-association foundation** | We create the association records, but the review screens don't yet *use* them to find the right records. So they still rely on the old, fragile link that other teams can overwrite. |
| 3 | **Effective-date accuracy across location changes** | Logic that keeps a provider's effective dates correct when locations are added/removed is designed; a one-time cleanup of ~230K existing records is also pending. |
| 4 | **Future-dated termination handling** | Pushing out a future termination date currently doesn't take effect (designed fix not built). |
| 5 | **All-or-nothing PAR submission** | Today a mid-process failure can leave partial/orphaned records. A redesign to make submission atomic is planned, not built. |
| 6 | **Concierge questions on the forms + downstream wiring** | The back-end is built, but the actual questions on the PAR and recred screens, and the add/terminate logic, are not live. |
| 7 | **Strategic redesigns** | Moving recred work onto the PAR process (batch), the recred→initial-cred conversion path, and the new tile-based screen redesign are all still in design/proposal stage. (Not required to resume.) |

---

## 3. Defects (currently broken — need to be fixed)

These are confirmed problems in the live system:

### High severity (data integrity / production blockers)

1. **Removing one location in Recred terminates ALL practitioners at that location.** *(QA Bug 1216121 — the "major issue")*
   When a location is removed during the Recred Update review, the system stamps an end (Effective-To) date on **every** practitioner at that location, not just the one being removed. This wrongly terminates providers. **Confirmed still present. Not fixed.**

2. **"Required Fields Missing" error on terminated locations.** Providers tied to a terminated location hit a hard error that blocks credentialing. A nightly script makes it worse by re-stamping stale records. (Real example: case IA-0000096229.) The warning banner detects it; the actual fix is **not deployed**.

3. **PAR form can leave partial / orphaned records.** When submission fails partway, leftover records remain and cause downstream errors. Described as "recurring and growing." **Not fixed.**

4. **Duplicate-record errors when an existing provider re-submits.** A set of provider/vendor combinations are blocked by duplicate errors. Some can be cleaned up by hand; a few require a code fix that is **not done**.

5. **Future-dated termination changes are silently ignored** (see Outstanding #4) — leaves inconsistent effective dates.

### Medium severity (workflow / display)

6. **Recred QC shows the wrong table on the "Errors Found" path.** *(QA Bug 1216120)*
   When QC selects the "Errors Found" outcome, the "Removed Practitioner at Practice Location…" table still displays even though it shouldn't. **Confirmed still present. Not fixed.** QA also flagged that the broader "Errors Found" scenario should be re-checked alongside this fix.

7. **PNC-path form issue** prevents certain already-credentialed providers from taking the correct path. **Not fixed.**

8. **Denied/terminated providers can't cleanly re-submit** due to leftover records colliding. **Not fixed.**

---

## 4. What needs to happen before we resume

In priority order:

**Must-fix before resuming guided location changes (Gate 1):**
1. Background processing for high-volume locations (Outstanding #1).
2. Fix the "removing a location terminates everyone" defect (Defect #1).
3. Fix the terminated-location "Required Fields Missing" error + the nightly script (Defect #2).
4. Make PAR submission all-or-nothing (Defect #3 / Outstanding #5).
5. Fix the QC "Errors Found" display issue and re-validate that path (Defect #6).

**Next, for data accuracy (Gate 2):**
6. Effective-date sync + the one-time cleanup (Outstanding #3).
7. Future-dated termination fix (Defect #5).
8. Switch the review screens to use the new case-association link (Outstanding #2).

**Then, feature completeness (Gate 3):**
9. Duplicate-record fix, PNC-path fix, denied/terminated re-submit fix (Defects #4, #7, #8).
10. Concierge questions on the forms, if in scope (Outstanding #6).
11. Strategic redesigns (Outstanding #7) — not prerequisites for resuming.

---

## 5. Decisions we need from the business

1. **Resume scope:** resume for **all** providers, or only **low-volume** locations first while we harden high-volume processing?
2. **Concierge:** is concierge capture needed in this resume, or can it wait? (Back-end is ready; the form questions are not.)
3. **Recred direction:** which strategic approach do we commit to — moving recred onto the PAR process, or the recred→initial-cred conversion path? (We should pick one.)
4. **Nightly script ownership:** confirm who owns the nightly job so its fix can be scheduled.

---

*This summary is based on a review of our requirement documents against the actual software in our codebase, plus the open defects reported by QA. "Built" reflects what exists in the codebase; the correct versions still need to be confirmed as switched on in production before any resume. A detailed technical companion to this summary is available in `Recred_PDA_PSV_Route_PAR_Form_Audit_2026-06-08.md`.*
