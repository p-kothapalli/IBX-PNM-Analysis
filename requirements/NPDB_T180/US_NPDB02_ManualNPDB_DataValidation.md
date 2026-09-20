# US-NPDB-02 — Manual NPDB Request: Tell the User Exactly What's Missing (Before They Submit)

**Status:** Draft for business sign-off
**Created:** 2026-06-01
**Updated:**
- *2026-06-01 (v1)* — Initial draft (pre-template format).
- *2026-06-03 (v2)* — Rewrite to IBXQA 11-section template + linter-conformant appendix.
- *2026-06-03 (v3)* — Rewrite to **User Story Solution Architect v1.6** skill: business-language ACs (Pattern A/B/C), separate **Technical Implementation (high-level)** section, canonical workspace persona.
- *2026-06-08 (v4)* — Design pivot after a component audit: replaced the deep-link banner with detailed, link-free text messages rendered natively in the OmniScript; validation moved into the Integration Procedure layer.
- *2026-06-08 (v5)* — **Rewritten for a business audience.** Plain-English throughout (record types described by what they mean, not by API name), and a full **Error Message Catalog** added (the exact wording the Credentialing Specialist sees for every missing-data scenario, for the participation, re-credentialing, and ancillary paths). Technical detail consolidated below the business stop-line.
**Author:** AI agent (with QA-sandbox evidence)
**Background investigation:** `00_Overview_NPDB_T180_Validation.md`, `01_Architecture_Diagrams.md`; component audit of the live **Request NPDB** OmniScript and its Integration Procedures (2026-06-08).
**Primary persona:** **Credentialing Specialist** — the operations role who clicks **Request NPDB** or works through an NPDB step inside a review flow. For ancillary facilities, the **Ancillary Cred Specialist** has the same expectations.

> **How to read this story.**
>
> - **Business sign-off audience** — read everything from *Story* down to the end of the **Error Message Catalog** and the **Acceptance Criteria**. You can stop at the *Technical Implementation* header.
> - **Developer audience** — same, plus the *Technical Implementation* block and *Definition of done*.
> - **QA audience** — the Acceptance Criteria are your test scripts, and the Error Message Catalog is the expected on-screen text to assert against.

---

## Header

**Persona:** Credentialing Specialist (primary); Ancillary Cred Specialist (ancillary facilities); Network Management QC Specialist (reviewer who hits an NPDB step inside a review flow)
**Priority:** P0
**The "Request NPDB" button appears for:** Re-Credentialing Case Managers, Participation-Request ("new practitioner joining") Case Managers, and Ancillary facility Case Managers. (It does **not** appear for the standard Initial Credentialing record — that path requests NPDB only from inside the review flow.)
**Relevant Requirements:** US-NPDB-01 (delivers the data check, the new fields, the new status, and the ready-to-display message text this story shows); US-NPDB-03 (reports on the resulting blocked queue); business NPDB-error backlog (May 2026).

---

## Story

**As a** Credentialing Specialist (or Ancillary Cred Specialist for ancillary facilities, or a reviewer who reaches an NPDB step inside a review flow),
**I want** the screen to tell me, **before I submit**, exactly which pieces of information are missing — written in plain English, grouped by the record I need to open, with a clear instruction for each one —
**So that** I know precisely what to fix, I never wait a day for the NPDB service to bounce a request I could have caught up front, and I never fire off a request that is guaranteed to fail.

**Why it matters:** Today, when a Credentialing Specialist clicks **Request NPDB**, the system creates the request and only checks one thing — whether the practitioner has a primary address. If anything else is missing (the NPI, a state license, an education record, or — for ancillary — the facility's practice NPI or affiliation address), the request is created anyway, goes out to the NPDB service, and **fails roughly a day later** with a vague error. The Specialist then either re-submits (and waits another day) or raises a ticket. Worse, when the one check *does* trip, the only message shown is **"No Active Location Found."**, which doesn't tell the user what to actually do. This story makes the screen list **every** missing item in plain language the first time, so the Specialist fixes it once and moves on. It pairs with US-NPDB-01, which performs the same check inside the nightly batch.

---

## Who sees this, and where

| The user is… | …doing this | …and now sees |
|---|---|---|
| Credentialing Specialist | Clicking **Request NPDB** on a **Participation-Request** ("new practitioner joining") Case Manager | The detailed missing-data message before the request is sent |
| Credentialing Specialist | Clicking **Request NPDB** on a **Re-Credentialing** Case Manager | The same detailed message |
| Ancillary Cred Specialist | Clicking **Request NPDB** on an **Ancillary facility** Case Manager | Per-facility missing-data messages on the practice-location step, plus practitioner-level messages on the final step |
| Reviewer (PSV / QC / App Review) | Reaching the NPDB step inside a review flow | The same detailed message, in the same words |
| Anyone | Opening a Case Manager that is blocked (status "NPDB Action Needed") | The same missing-data list, shown read-only on the record page |

---

## Preconditions

- **US-NPDB-01 is live.** The data check, the "Validation Details" and "Validation Last Run" fields, the new **NPDB Action Needed** status, and the business-maintained list of required fields all exist in the org.
- The user already has the permission that lets them see the **Request NPDB** button (this story does not change who can see the button).

---

## Error Message Catalog (the exact words the user sees)

> This is the heart of the story for business sign-off. Every message below is the **literal on-screen text**. Messages are assembled into one readable block, grouped by the record the user must open. Only the items that are actually missing are shown. Items marked **(blocks submission)** must be fixed before the request can go out; items marked **(warning only)** are shown but do not stop the request.

### A. Heading shown above the list

When one or more required items are missing, the message opens with:

> **We can't request the NPDB report yet.**
> Please fix the items below on the practitioner's record, then click **Request NPDB** again.

When everything is complete, no message is shown and the request submits normally.

---

### B. Practitioner detail messages (Participation-Request, Re-Credentialing, and Ancillary)

These apply to every record type, because NPDB always needs the practitioner's core details.

**Practitioner details**
- **(blocks submission)** "Date of birth is missing. Add the practitioner's date of birth on their record."
- **(blocks submission)** "Legal name is missing. Add the practitioner's legal name on their record."

**National Provider Identifier (NPI)**
- **(blocks submission)** "No active NPI is on file for this practitioner. Add an NPI record."
- **(blocks submission)** "An NPI record exists but the NPI number is blank. Enter the 10-digit NPI number."

**Primary address**
- **(blocks submission)** "The street address (line 1) is missing. Add it to the practitioner's primary address."
- **(blocks submission)** "The city is missing. Add it to the practitioner's primary address."
- **(blocks submission)** "The state is missing. Add it to the practitioner's primary address."
- **(blocks submission)** "The ZIP code is missing. Add it to the practitioner's primary address."
- **(warning only)** "The county is missing. NPDB accepts a blank county, but please add it if you know it."

**State license**
- **(blocks submission)** "No active state license is on file. Add the practitioner's state license, including the license number and the state that issued it."
- **(blocks submission)** "The license number is missing. Add it to the practitioner's state license."
- **(blocks submission)** "The issuing state is missing. Add it to the practitioner's state license."

**Education**
- **(blocks submission)** "No education record is on file. Add at least one education record (school, degree, and dates) for this practitioner."

---

### C. Facility messages (Ancillary only)

For an ancillary facility Case Manager, the user first selects one or more practice locations. The system then checks each selected location and lists problems **by facility name** so the user knows exactly which one to fix.

**Before any location is selected**
- **(blocks continuing)** "Please select at least one practice location before requesting the NPDB report."

**For each selected facility (the facility's name is shown in the heading)**
- **(blocks submission)** "{Facility name} — the facility's practice NPI is missing. Add the practice NPI for this location."
- **(blocks submission)** "{Facility name} — the affiliation street address is missing. Add it on this location's affiliation details."
- **(blocks submission)** "{Facility name} — the affiliation city is missing. Add it on this location's affiliation details."
- **(blocks submission)** "{Facility name} — the affiliation state is missing. Add it on this location's affiliation details."
- **(blocks submission)** "{Facility name} — the affiliation ZIP code is missing. Add it on this location's affiliation details."

**Additional checks for ancillary Re-Assessment**
- **(blocks submission)** "{Facility name} — the Tax ID is missing. Add the Tax ID for this location."
- **(blocks submission)** "{Facility name} — the Medicare number is missing. Add the Medicare number for this location."

---

### D. Status messages (unchanged behaviour, listed here for completeness)

These already exist and are kept as-is so nothing regresses:

- **Already being processed:** "An NPDB report has already been requested for this practitioner and is currently being processed. You don't need to request it again."
- **Requested in the last 24 hours:** "An NPDB report was requested for this practitioner within the last 24 hours. Please wait until the 24-hour window has passed before requesting again."
- **Success:** "Your NPDB request has been submitted. We'll alert you when the report is received."

---

### E. Worked example (what a real screen looks like)

For a participation-request practitioner missing a street address, an NPI, and a license, the user sees:

> **We can't request the NPDB report yet.**
> Please fix the items below on the practitioner's record, then click **Request NPDB** again.
>
> **Primary address**
> • The street address (line 1) is missing. Add it to the practitioner's primary address.
>
> **National Provider Identifier (NPI)**
> • No active NPI is on file for this practitioner. Add an NPI record.
>
> **State license**
> • No active state license is on file. Add the practitioner's state license, including the license number and the state that issued it.

---

## Acceptance Criteria

> Pattern A (Given/When/Then) for behaviour the user observes. Pattern C for permissions. The expected on-screen wording is the **Error Message Catalog** above.

### The detailed message replaces the vague one

**AC-2.1 — Missing information is listed in plain English before anything is sent**

**Given** a practitioner whose record is missing one or more pieces of information NPDB needs,
**When** the Credentialing Specialist clicks **Request NPDB**,
**Then** the screen shows the heading and the grouped list of missing items exactly as written in the Error Message Catalog (Sections A and B),
**And** the **Request NPDB** action is disabled until every item marked *(blocks submission)* is fixed,
**And** no NPDB request is created.

---

**AC-2.2 — Each line tells the user what to open and what to do**

**Given** the missing-information message is showing,
**When** the user reads any line,
**Then** the line names the record to open (the practitioner's details, primary address, NPI, license, education, or a named facility) and the action to take ("add", "enter", "fix"),
**And** there are no record ID numbers, system codes, or links in the message — it reads like guidance, not a system error.

---

**AC-2.3 — The check runs again when the user fixes the data and retries**

**Given** the user has read the message, opened the right record, added the missing information, and saved,
**When** they return and click **Request NPDB** again,
**Then** the items they fixed disappear from the list and anything still missing remains,
**And** once nothing that blocks submission is left, the message clears, the request is sent, and the user sees the success message,
**And** the existing 24-hour "don't request twice" rule still applies.

---

**AC-2.4 — A warning-only item does not stop the request**

**Given** the only thing missing is the county on the primary address,
**When** the user clicks **Request NPDB**,
**Then** the county warning is shown for awareness,
**But** the request is **not** blocked and submits normally.

---

### Participation-Request ("new practitioner joining")

**AC-2.5 — The participation-request button shows the full list, not just "No Active Location Found"**

**Given** a Participation-Request Case Manager (a new practitioner joining) with incomplete information,
**When** the Credentialing Specialist clicks **Request NPDB**,
**Then** instead of the old generic "No Active Location Found." message, the screen shows the complete grouped list from the Error Message Catalog (Section B),
**And** if the practitioner's information is complete, no message appears and the request submits exactly as it does today.

---

### Re-Credentialing

**AC-2.6 — Re-credentialing shows the same detailed list**

**Given** a Re-Credentialing Case Manager with incomplete information,
**When** the Credentialing Specialist clicks **Request NPDB**,
**Then** the same plain-English grouped list (Section B) is shown with the same wording and the same "fix before you can submit" behaviour.

---

### Ancillary facilities

**AC-2.7 — Facility problems are listed by facility name on the practice-location step**

**Given** an ancillary facility Case Manager where the user has selected one or more practice locations and at least one has missing facility or affiliation information,
**When** the user tries to move past the practice-location step,
**Then** the screen lists each problem by facility name exactly as written in the Error Message Catalog (Section C) — for example *"Riverside Clinic — the affiliation street address is missing…"* —,
**And** the user cannot continue until every facility item that blocks submission is fixed (the "select at least one location" rule still applies),
**And** for an ancillary Re-Assessment, the Tax ID and Medicare number checks are included.

---

**AC-2.8 — Ancillary also checks the practitioner's core details**

**Given** an ancillary facility Case Manager whose selected facilities are complete but whose practitioner details (NPI, license, education, date of birth) are incomplete,
**When** the user reaches the final step,
**Then** the same practitioner-level list (Section B) is shown,
**And** the request is not sent until both the facility problems and the practitioner problems are cleared.

---

### Same words everywhere NPDB is requested

**AC-2.9 — The review flows show the identical message**

**Given** the user reaches the NPDB step inside any review flow (PSV Review, Initial Credentialing App Review, Credential App Review Complete, or Re-Cred QC Review),
**When** the practitioner's information is incomplete,
**Then** they see the same grouped, plain-English list, in the same words, with the same "fix before you can submit" behaviour,
**And** the user does not have to learn a different screen for each flow.

---

### Behind-the-scenes safety net

**AC-2.10 — Requests created by automated jobs are blocked the same way**

**Given** an automated job or a back-end process tries to create an NPDB request for a practitioner whose information is incomplete (for example, the nightly job that retries a previously-failed request),
**When** that request is created,
**Then** the system refuses it,
**And** the Case Manager is quietly moved to **NPDB Action Needed** with the same missing-information list recorded on it,
**And** no NPDB call is ever made,
**And** end users see nothing — this is a back-end safeguard so no path can sneak past the check.

---

**AC-2.11 — Administrators can still override for production support**

**Given** an administrator holds the existing production-support override permission,
**When** they create an NPDB request through a back-end process,
**Then** the safeguard in AC-2.10 lets it through,
**And** the override is recorded for the audit trail (who did it and for which Case Manager).

---

### On the record page

**AC-2.12 — The missing-information list is also visible on the Case Manager record page**

**Given** a Case Manager that is currently blocked (status **NPDB Action Needed**),
**When** the user opens the Case Manager record page,
**Then** the same plain-English missing-information list is shown, read-only, in the right-hand area of the page,
**And** the list disappears on its own once the information is complete,
**And** nothing on the existing page is hidden, moved, or resized.

---

### No change to who can request NPDB

**AC-2.13 — Users without the right permission still don't see the button or the message**

**Given** a user who does not have the permission to request NPDB,
**When** they open any Case Manager,
**Then** the **Request NPDB** button still does not appear, and the missing-information message does not appear either,
**And** nothing about their experience changes.

---

### Performance

**AC-2.14 — The check is instant**

**Given** the check runs as part of the request the user already triggers,
**When** the screen evaluates the practitioner's information,
**Then** the result appears within about a second for a typical practitioner (and within about two seconds for one with many missing items),
**And** the page does not feel slower to load.

---

## Technical Section — Technical Implementation (high-level)

> **Design principle (v4/v5):** validate where the data already lives, and keep the message wording in one place. The NPDB Integration Procedure already loads the practitioner's address, NPI, education, and licensure to build the request; it simply never *checked* them. We add the check there, return a ready-to-display, link-free message string (`detailText`, delivered by US-NPDB-01), and render it with native OmniScript Message + Validation elements. The Error Message Catalog above is the canonical wording for that `detailText`.

| Component | Type | Change | Drives |
|---|---|---|---|
| `PRM_NpdbDataValidator` (US-NPDB-01) | Consumed | Produces the `detailText` whose wording matches the Error Message Catalog. Wording lives in US-NPDB-01's metadata-driven field config (friendly label + fix instruction per rule). | All ACs |
| `PRM_IPCreateAdverseActionLog` (child IP) | Modify (new version) | Call the validator before the request-create steps; output `npdbValid` + `npdbDetailText`. Gate the request-create steps on `npdbValid = true`. Retire/replace the old address-only "No Active Location Found" check. | AC-2.1 → 2.6, 2.8, 2.14 |
| `PRM_GetAncNpdbDetails` (ancillary IP) | Modify (new version) | Build the per-facility message text (grouped by facility name) for missing practice NPI + affiliation address (+ Tax ID / Medicare for Re-Assessment). Output `npdbFacilityValid` + `npdbFacilityDetailText`. | AC-2.7 |
| `PRM_CallNPDB_English` (active `_2` → new `_3`) | OmniScript version bump | Final step: replace the generic message with a detailed **Message** element bound to `npdbDetailText` + a **Validation** (Requirement) that blocks submit while `npdbValid = false`. Practice-location step (ancillary): add a **Message** bound to `npdbFacilityDetailText` + Validation blocking Next, alongside the existing "select a row" rule. Keep the existing status messages. | AC-2.1, 2.5, 2.6, 2.7, 2.8 |
| `PRM_PSVSubOsWSNPDB_English`, `PRM_InitialCredentialAppReview_English`, `PRM_CredentialAppReviewCompleteOS_English`, `PRM_RecredQC_English` | OmniScript version bumps | Inject the same validator call + detailed Message + Validation before each NPDB sub-step. | AC-2.9 |
| `PRM_AdverseActionLogTrigger` + `PRM_AdverseActionLogTriggerHandler` | New Apex trigger + handler | Before-insert safety net over every request-create path; blocks incomplete-data inserts, flips the Case Manager to **NPDB Action Needed**, respects the existing production-support override. | AC-2.10, 2.11 |
| `PRM_FlipCmToActionNeededQueueable` | New Apex Queueable | Moves the Case Manager to **NPDB Action Needed** and records the missing-info list; idempotent. | AC-2.10 |
| Record-page findings surface | New (read-only) | Renders the recorded missing-info list as plain text in the right-rail; no links, auto-hides when empty. | AC-2.12 |
| `PRM_CaseManagerRecordPage`, `PRM_NonParCaseMangerRecordPage` FlexiPages | Modify | Add the read-only surface to the right-rail. | AC-2.12 |
| Permission set updates (3 sets) | Modify | Access to run the validator + see the record-page surface. | AC-2.13 |
| Apex + Jest test classes | New + modify | Cover the trigger gate, the queueable, the batch/reinitiate integration, and the message rendering. | Quality gate |

> The request wrapper (`PRM_IPCreateAdverseActionLogParent`) and the underlying request-create DataRaptors are **not** changed — the check sits in the child IP (for the user message) and in the Apex trigger (for the back-end safety net), so every path uses the same rules and the same wording.

---

## Definition of done

- [ ] The validator's message wording (delivered by US-NPDB-01) matches this story's Error Message Catalog, reviewed and signed off by the business.
- [ ] `PRM_IPCreateAdverseActionLog` republished: validator call added, request-create steps gated; `PRM_GetAncNpdbDetails` republished with per-facility messages.
- [ ] All five OmniScripts (Request NPDB + the four review flows) republished with the detailed Message + Validation elements; prior versions deactivated.
- [ ] Back-end safety net (trigger + handler + queueable) deployed with tests at ≥85% overall and ≥95% on the handler.
- [ ] Record pages updated with the read-only missing-info surface.
- [ ] Permission set updates deployed.
- [ ] QA smoke test for each path — a complete practitioner (submits cleanly) and an incomplete one (shows the right message and blocks) — including a Participation-Request practitioner (AC-2.5) and an ancillary facility with a missing affiliation address (AC-2.7).
- [ ] QA smoke test for the safety net: a back-end request for an incomplete practitioner is blocked and the Case Manager flips to **NPDB Action Needed**.

---

## Impact Analysis

| Area | Impact | Notes |
|---|---|---|
| NPDB request Integration Procedure | HIGH | The check is added inside the live request path; today's clean-data flow must be preserved exactly. |
| Ancillary details Integration Procedure | MEDIUM | Adds per-facility message text. |
| Five OmniScripts | HIGH | Five active scripts re-versioned at once — coordinate to avoid conflicts with other in-flight changes. |
| Back-end safety net (new trigger) | HIGH | New check over every request-create path; must be bulk-safe. |
| Record pages (2) | MEDIUM | Right-rail-only edits to minimise regression risk. |
| Record-page surface | LOW | Read-only text; much smaller than the previously-proposed link banner. |
| Permission sets (3) | LOW | Access only — no field-security changes here (those came with US-NPDB-01). |
| Request wrapper IP + request-create DataRaptors | NONE | Not changed. |
| Retry/clone jobs | MEDIUM | Incomplete-data requests now blocked at creation time; integration tests must confirm. |

---

## Clarification Questions (before implementation)

| # | Question | Default |
|---|---|---|
| Q1 | Show the read-only missing-info list on the Case Manager record page at launch (AC-2.12), or as a fast-follow? | Include at launch. |
| Q2 | Does the Participation-Request path require exactly the same information as Re-Credentialing? | Yes — identical, until the business says otherwise. |
| Q3 | Does ancillary Re-Assessment require anything beyond ancillary Assessment? | Same, plus Tax ID and Medicare number (AC-2.7). |
| Q4 | Build the record-page surface as a small display component or as a read-only page section? | Small display component (cleaner auto-hide). Either is link-free. |
| Q5 | Final sign-off on the exact wording in the Error Message Catalog. | Use as written; adjust per business review. |

---

## Estimated Effort

> AI-estimated — validate with team.

| Component | Effort | Notes |
|---|---|---|
| Add the check + message output to the NPDB request IP | **L** | Validate data already loaded; gate the create steps. |
| Add per-facility messages to the ancillary details IP | **L** | Group by facility name. |
| Inject message + validation into 5 OmniScripts | **XL** | Version + republish + deactivate prior; biggest risk is coordinating across active scripts. |
| Read-only record-page surface | **M** | Read-only text, no navigation logic. |
| Record-page edits (2) | **M** | Standard config. |
| Back-end safety net (trigger + handler) | **L** | Single chokepoint; respects existing override. |
| Move-to-blocked queueable | **M** | Idempotent. |
| Test classes | **XL** | ≥95% on the handler. |
| Permission set updates (3) | **S** | Access only. |
| Deploy + QA across all paths | **L** | See Definition of done. |
| **Total** | **~XL (≈ 5–6 dev-days incl. testing + QA)** | **13 story points** — confidence Medium. Lower UI-regression risk than the deep-link approach; main risk is the five-OmniScript re-version. |

---

## Revision History

| Version | Date | Summary |
|---------|------|---------|
| v1 | 2026-06-01 | Initial draft (pre-template format). |
| v2 | 2026-06-03 | Rewrite to IBXQA Pre-Development Story Analysis Template + linter-conformant appendix. |
| v3 | 2026-06-03 | Rewrite to **User Story Solution Architect v1.6**: Pattern A/B/C ACs, separated Technical Implementation, canonical persona. |
| v4 | 2026-06-08 | Design pivot after a live-component audit: detailed, link-free text messages rendered natively in the OmniScript (Message + Validation), driven by the validator's `detailText`; validation moved into the request Integration Procedure; PAR and Ancillary behaviours split out. |
| v5 | 2026-06-08 | **Rewritten for a business audience.** All sections in plain English (record types described by meaning, not API name); added the full **Error Message Catalog** (exact on-screen wording for every missing-data scenario across participation, re-credentialing, and ancillary, plus the status messages and a worked example). ACs reworded to business terms and re-numbered; technical detail consolidated below the business stop-line. |
