# USER STORY: PSV Review — License / Taxonomy / DEA Verification Display & DEA Expiry Handling

**Persona:** PSV Specialist
**Priority:** P1
**OmniScript:** `PRM_PrimarySourceVerificationReview_English` (active version **51**)
**Integration Procedures:** N/A directly on-flow; downstream save writes into `BusinessLicense` (DEA record type) via the parent OmniScript's output map (`DEALicenses`, `SBRDLicenses`, `Taxonomies` properties consumed by the case-close IP chain)
**Relevant Requirements:**
- QA test Case Manager referenced by business: `IndividualApplication` Id `0iTVB000000Jf4H2AS` (Case Id `500VB00000hG2Zr`) — feedback captured in-chat 2026-08-16.
- Cross-reference — different PSV step, no code overlap: `requirements/PSV_ServiceAreaVerification_CAQHBulkLocation_DataMapper_BugFix_UserStory.md` (Service Area Verification bulk transform bug).
- Cross-reference — ReCred flow reuses the same OmniScript output map: `requirements/ReCred_PSV_to_RCAT_DirectPush_Guide.md`.

---

## Story

**As a** PSV Specialist,
**I want** the License, Taxonomy, and DEA Verification steps of Primary Source Verification to show only the source-of-truth data that I actually verify against, and to stop me from saving expired DEA information onto the practitioner,
**So that** my PSV review is not slowed down by redundant CAQH panels, my taxonomy sign-off is unambiguous, and no expired DEA data flows downstream to Case Closure / QC / PDA.

**Why it matters:** PSV Specialists today are shown *two* copies of the same fact (License, Specialty) on multiple steps — one from CAQH, one from the PAR form — which forces them to reconcile duplicates that were never in conflict, and gives no clear source of truth. Worse, on the DEA step the OmniScript writes **every** CAQH DEA record — including expired ones — down to `BusinessLicense` (DEA record type) when the specialist clicks Continue, so expired DEA data reaches downstream QC / Committee / PDA reviewers and, if *all* CAQH DEA rows are expired, the specialist has no visual cue that manual outreach is required.

---

## Scope

| # | Verification Step (in parent OmniScript v51) | Change | Phase |
|---|---|---|---|
| 1 | **License Verification** — currently displays *both* the CAQH-sourced business license block (`VerifyLicense:BusinessLicensePractitioner`) **and** a PAR-form-captured license text block (`TextBlockLicenseReadOnly`, reads `PractitionerForm:PractitionerLicenseNumber`). | Hide the PAR-form-captured license; keep only the CAQH-sourced license row. | Post Go-Live |
| 2 | **Taxonomy / Specialty Verification** — currently displays a specialty read-only element (`ReviewPractitionerSpecialty` from PAR form) alongside CAQH-sourced specialty rows in the verify block. Taxonomy **code** is not shown in the table. | (a) Add Taxonomy Code column to the specialty table. (b) Hide the CAQH-specialty column; display only the PAR-form-captured specialty as the source of truth. | Phase 2 |
| 3a | **DEA Verification (near-term)** — save formula `DEALicenses = IF(%DEAVerificationOutcome% == "Data Looks Good", %DEAVerification:DEABusinessLicense%, [])` writes every DEA row from CAQH, expired or not; no visual signal when every CAQH DEA is expired. | (i) Filter the save so only DEA rows where **Expiration Date ≥ today** are written. (ii) Show a non-blocking warning banner on the DEA step when **all** CAQH DEA rows are expired. | Near-term |
| 3b | **DEA Verification (Phase 2)** — the CAQH DEA display section is redundant to the practitioner's DEA panel. | Hide the CAQH DEA display section. | Phase 2 |

Explicitly **out of scope for this story:**
- Sub-OmniScripts `PRM_PSVSubOsSummary_English`, `PRM_PSVSubOsWSNPDB_English`, `PRM_PSVSubOsTxnyRole_English` — no changes.
- The typo `LicenseVerifcation` (missing "i") at line 6886 of the OmniScript — a separate cleanup item.
- CDS Verification step — parallel design but not requested.
- The Service Area Verification bulk-transform bug — already covered by its own P0 story.

---

## Current State (from codebase — `PRM_PrimarySourceVerificationReview_English_51.os-meta.xml`)

### License Verification step (redundancy)

- **Element `TextBlockLicenseReadOnly`** (Text Block, line 4012) — reads `PractitionerForm:PractitionerLicenseNumber` (PAR-form-captured), rendered above the CAQH license block.
- **Element `VerifyLicense`** (Verify Block) — reads `BusinessLicensePractitioner` from the CAQH-shaped payload; outputs to `SBRDLicenses` at save (line 6886): `SBRDLicenses = IF(%LicenseVerifcation% == "Data Looks Good", %VerifyLicense:BusinessLicensePractitioner%, [])`.
- **Result:** two license rows shown for a practitioner whose PAR-form license and CAQH license are the same record — nothing to reconcile, redundant UI.

### Taxonomy / Specialty Verification step (redundancy + missing code)

- **Element `ReviewPractitionerSpecialty`** (line 3752) — read-only, reads `PractitionerForm:PractitionerPrimarySpecialty|1:Name` (PAR-form-captured).
- **Element `ReviewProviderAdditionalSpecialty`** (line 3835) — read-only, PAR-form additional specialties.
- **Element `SetPractitionerSpecialtyFields`** (line 6596) — sets `VerifyTaxonomyPractitioner`, `VerifyCareTaxonomyPractitioner` (= `PractitionerPrimarySpecialty|1:Taxonomy:Name`), `VerifyPrimaryTaxonomyPractitioner`.
- **Element `VerifySpecialty:VerifyPractitionerSpecialty`** — displays CAQH-sourced specialty rows; outputs to `Taxonomies` at save (line 6889): `Taxonomies = IF(%SpecialtyVerification% == "Data Looks Good", %VerifySpecialty:VerifyPractitionerSpecialty%, [])`.
- **Missing today:** the taxonomy **code** (a field on the underlying Taxonomy record — surfaced via `PractitionerPrimarySpecialty|1:Taxonomy:Code` or equivalent) is not rendered as a column in the specialty table.

### DEA Verification step (expired-DEA leak + redundant CAQH panel)

- **Save formula (line 6884)** — parent PSV / PAR path:
  `"DEALicenses" : "=IF(%DEAVerificationOutcome% == \"Data Looks Good\", %DEAVerification:DEABusinessLicense%, [])"`.
- **Save formula (line 7053)** — ReCred path:
  `"DEALicenses" : "=IF(%ReCredDEAVeriFRML% == \"Data Looks Good\", %DEAVerification:DEABusinessLicense%, [])"`.
- **Save formula (line 7184)** — Off-Cycle / RCAT path (same shape).
- **Result today:** every DEA row in `DEAVerification:DEABusinessLicense` is written to `DEALicenses`, expired or not. There is no filter on Expiration Date and no visual indication when every CAQH DEA is expired.

**Same OmniScript serves PAR, ReCred, and Off-Cycle/RCAT paths** — anything we change here must be tested against all three (see Impact Analysis).

---

## Acceptance Criteria

> Every behavioural AC is Pattern A (Given / When / Then, single When, business language). AC-6 pairs a Pattern A behavioural AC with a **Pattern E** per-object field specification for the DEA record write (RULE 15).

### Group 1 — License Verification (Post Go-Live)

**AC-1 — Only the CAQH-sourced business license is displayed on the License Verification step**

**Given** a PSV Specialist opens the License Verification step for a practitioner whose PAR form and CAQH profile both contain the same license,
**When** the step renders,
**Then** only the CAQH-sourced business license row is displayed,
**And** the PAR-form-captured license text (currently shown as a separate read-only block above the CAQH row) is no longer displayed.

**AC-2 — No regression to the License save contract**

**Given** the PSV Specialist verifies the license (marks the outcome "Data Looks Good") and clicks Continue,
**When** the OmniScript saves,
**Then** the same license record is saved to the practitioner as today,
**And** the downstream Case-Close review reviewers (QC / Committee / PDA) see the same license information they see today (this change is display-only for the PSV step).

### Group 2 — Taxonomy / Specialty Verification (Phase 2)

**AC-3 — Taxonomy Code column is visible in the specialty table**

**Given** a PSV Specialist opens the Specialty Verification step for a practitioner whose primary specialty on the PAR form maps to a taxonomy record,
**When** the step renders,
**Then** the specialty table displays a **Taxonomy Code** column alongside the specialty name,
**And** the code shown is the taxonomy record's code as maintained on the taxonomy master data.

**AC-4 — Only the PAR-form-captured specialty is displayed; CAQH-sourced specialty column is hidden**

**Given** a PSV Specialist opens the Specialty Verification step,
**When** the step renders,
**Then** the specialty row shown is the specialty captured on the PAR form (primary specialty plus any additional specialties captured on the PAR form),
**And** the previously displayed CAQH-specialty column is no longer visible on the step,
**And** the specialty saved to the practitioner continues to be the PAR-form-captured specialty (the source of truth remains the PAR form).

### Group 3 — DEA Verification (near-term + Phase 2)

**AC-5 — Non-blocking warning banner when all CAQH DEA rows are expired**

**Given** a PSV Specialist opens the DEA Verification step for a practitioner where every CAQH DEA record has an Expiration Date earlier than today,
**When** the step renders,
**Then** a non-blocking warning banner is displayed on the DEA step reading, in business language, "All CAQH DEA records for this practitioner are expired — please review with the practitioner or the credentialing lead before continuing.",
**And** the PSV Specialist can still mark the DEA outcome and click Continue (the banner does not block progression).

**AC-6 — Only non-expired DEA records are saved from the DEA Verification step**

**Given** a PSV Specialist marks the DEA outcome "Data Looks Good" and clicks Continue on a practitioner whose CAQH DEA payload contains a mix of expired and non-expired DEA records,
**When** the OmniScript saves,
**Then** only DEA records where the Expiration Date is on or after today are saved to the practitioner's DEA record,
**And** no expired DEA record is created for that practitioner as part of this PSV save.

**AC-6-E — Pattern E: fields written on the DEA save (per DEA row that survives the filter)**

| Object | Record Type | Field | Value / Formula | Notes |
|---|---|---|---|---|
| `BusinessLicense` | `DEA` (or the org's DEA business license record type — verify against `PRMDRUpsertBusinessLicense` naming) | `LicenseNumber` | `%DEAVerification:DEABusinessLicense[i]:LicenseNumber%` | as today |
| `BusinessLicense` | `DEA` | `IssuingAuthority` | `%DEAVerification:DEABusinessLicense[i]:IssuingAuthority%` | as today |
| `BusinessLicense` | `DEA` | `IssuedDate` (Effective From) | `%DEAVerification:DEABusinessLicense[i]:IssuedDate%` | as today |
| `BusinessLicense` | `DEA` | `ExpirationDate` | `%DEAVerification:DEABusinessLicense[i]:ExpirationDate%` | **must be ≥ TODAY() for the row to be written** — this is the new filter |
| `BusinessLicense` | `DEA` | `Status` | `%DEAVerification:DEABusinessLicense[i]:Status%` | as today |
| `BusinessLicense` | `DEA` | `LicenseClass` / `Schedule` | `%DEAVerification:DEABusinessLicense[i]:LicenseClass%` | as today |
| `BusinessLicense` | `DEA` | `LicenseTypeCategory` | `"DEA"` | as today |
| `BusinessLicense` | `DEA` | `ContactId` (Practitioner) | `%PractitionerForm:PractitionerBusinessLicense|1:ContactId%` | inherited from parent context |
| `BusinessLicense` | `DEA` | `HealthcareProviderId` | `%PractitionerForm:PractitionerBusinessLicense|1:HealthcareProvider:Id%` | inherited from parent context |
| `BusinessLicense` | `DEA` | External Id (upsert key) | as configured on `PRMDRUpsertBusinessLicense` today | **verify with build team — see Clarification Q3** |

> **Filter rule** (applied *before* the object is written): a DEA row from `%DEAVerification:DEABusinessLicense%` is included **only if** `ExpirationDate >= TODAY()`. Expired rows are dropped from `DEALicenses` and no `BusinessLicense` record is written for them.

**AC-7 — No warning when at least one non-expired CAQH DEA exists**

**Given** a PSV Specialist opens the DEA Verification step for a practitioner where at least one CAQH DEA record has Expiration Date on or after today,
**When** the step renders,
**Then** the warning banner from AC-5 is not displayed,
**And** the DEA step behaves as it does today (aside from the save-time filter in AC-6).

**AC-8 — Edge case: no CAQH DEA rows returned at all**

**Given** a PSV Specialist opens the DEA Verification step for a practitioner whose CAQH profile returns zero DEA records,
**When** the step renders,
**Then** the step behaves exactly as today for a no-DEA practitioner (no warning banner from AC-5, since "all rows expired" is not the case),
**And** no `BusinessLicense` (DEA) record is created on save.

**AC-9 — Phase 2: hide the CAQH DEA display section**

**Given** the Phase 2 change is deployed,
**When** a PSV Specialist opens the DEA Verification step,
**Then** the CAQH-sourced DEA display block is no longer visible on the step,
**And** the DEA save contract (per AC-6 / AC-6-E) is unchanged — the source data for the save continues to be the CAQH DEA payload, filtered by expiration.

---

## Technical Implementation (high-level)

| # | Component | Type | Change | AC it implements |
|---|---|---|---|---|
| T1 | `PRM_PrimarySourceVerificationReview_English` (new version cloned from v51) | OmniScript | Hide element `TextBlockLicenseReadOnly` (or move its `showCondition` to `false`) on the License Verification step. Keep the `VerifyLicense` block untouched. | AC-1, AC-2 |
| T2 | `PRM_PrimarySourceVerificationReview_English` (Phase 2) | OmniScript | Add a Taxonomy **Code** column to the specialty verify block; source: `PractitionerForm:PractitionerPrimarySpecialty|1:Taxonomy:Code` (or equivalent — verify on the Taxonomy master record; see Clarification Q4). | AC-3 |
| T3 | `PRM_PrimarySourceVerificationReview_English` (Phase 2) | OmniScript | Hide the CAQH-specialty column in the specialty verify block; keep `ReviewPractitionerSpecialty` (PAR-form) as the sole displayed specialty. Save contract for `Taxonomies` output property remains driven by `%VerifySpecialty:VerifyPractitionerSpecialty%` — do not repoint. | AC-4 |
| T4 | `PRM_PrimarySourceVerificationReview_English` — DEA Verification step | OmniScript | Add a **Formula element** `AllCAQHDEAExpired` computed as `COUNT(FILTER(%DEAVerification:DEABusinessLicense%, ExpirationDate < TODAY())) == COUNT(%DEAVerification:DEABusinessLicense%) AND COUNT(%DEAVerification:DEABusinessLicense%) > 0`. Add a **Message Block** on the DEA step with `showCondition = %AllCAQHDEAExpired% == true` displaying the AC-5 banner text. | AC-5, AC-7, AC-8 |
| T5 | `PRM_PrimarySourceVerificationReview_English` — DEA save formulas (lines 6884, 7053, 7184) | OmniScript | Change the three `DEALicenses` output-map formulas from `%DEAVerification:DEABusinessLicense%` to `FILTER(%DEAVerification:DEABusinessLicense%, ExpirationDate >= TODAY())`. Applies to PAR, ReCred, and Off-Cycle/RCAT paths. | AC-6, AC-8 |
| T6 | Downstream DataRaptor / IP that consumes `DEALicenses` (verify via `code-review-graph query_graph pattern=callees_of`) | DataRaptor / IP | **No functional change expected** — same shape, fewer rows. Run regression tests on the DEA upsert path to confirm. | AC-2, AC-6 |
| T7 | `PRM_PrimarySourceVerificationReview_English` — CAQH DEA display block (Phase 2) | OmniScript | Set `showCondition` on the CAQH DEA display block to `false` (or delete the element in the Phase 2 version). | AC-9 |

Version-cutting policy: create **one** new active version of the parent OmniScript per phase (Post-Go-Live version for T1; a subsequent Phase-2 version for T2/T3/T7). Near-term DEA changes (T4/T5) go in with the Post-Go-Live version. Only one version carries `isActive=true` at any point.

---

## Definition of done

- [ ] Only the CAQH business license row is visible on License Verification for the test Case Manager `IndividualApplication` `0iTVB000000Jf4H2AS` (AC-1).
- [ ] License save payload (`SBRDLicenses`) is byte-identical to pre-change for the same test case (AC-2).
- [ ] Specialty table shows Taxonomy Code column for a practitioner with a primary specialty on the PAR form (AC-3). *(Phase 2)*
- [ ] Only the PAR-form-captured specialty row is visible on Specialty Verification for the test case (AC-4). *(Phase 2)*
- [ ] Non-blocking warning banner appears on the DEA step when the entire CAQH DEA payload is expired; specialist can still click Continue (AC-5).
- [ ] Expired DEA rows are dropped from `DEALicenses` on save; only non-expired DEA rows are written as `BusinessLicense` (DEA record type); every field in the AC-6-E Pattern E table is populated exactly as specified (AC-6, AC-6-E).
- [ ] No warning banner when at least one non-expired DEA row exists (AC-7).
- [ ] Zero-DEA practitioners are unaffected (AC-8).
- [ ] Phase 2: CAQH DEA display block is hidden (AC-9). *(Phase 2)*
- [ ] Regression: PAR (Initial Cred), **ReCred**, and **Off-Cycle / RCAT** paths through PSV all pass end-to-end save; downstream Case Closure IP chain receives the expected `DEALicenses` / `SBRDLicenses` / `Taxonomies` payloads.
- [ ] FLS confirmed: all field reads used by the new formula (`ExpirationDate` on the CAQH-shaped payload) are already accessible to the PSV Specialist profile.
- [ ] Only one version of `PRM_PrimarySourceVerificationReview_English` is active in QA after deploy.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| Q1 | Does the business want the warning banner (AC-5) to remain **non-blocking** in production, or should it turn blocking after a grace period once specialists get used to seeing it? | Determines whether to design a togglable Custom Setting for the block/warn mode. | Product / Cred Ops |
| Q2 | On the DEA "expired" check — is `Expiration Date < today` the sole criterion, or is there a separate CAQH DEA status field (e.g. "Active"/"Expired") that should also be considered? Current story assumes date only. | Filter logic in T5. | CAQH integration SME |
| Q3 | The DEA upsert downstream (`PRMDRUpsertBusinessLicense` or equivalent) — what is the External Id it uses today, and do we need to confirm expired rows are not being upserted-then-inactivated somewhere else in the chain? | If a downstream node inactivates rather than skips, the AC-6 filter is redundant / cosmetic. | Build team / Cred backend |
| Q4 | For the Taxonomy Code column (AC-3), is the code sourced from `Taxonomy:Code` on the PractitionerPrimarySpecialty relation, or from a separate Custom Metadata / Custom Object? | Determines the merge-field path in T2. | Cred taxonomy SME |
| Q5 | Should the ReCred and Off-Cycle/RCAT paths receive the display changes (AC-1, AC-3, AC-4, AC-9) as well, or only the PAR / Initial Cred path? Story assumes **all three paths** get the same display changes because they share the same OmniScript. | Whether we need version-fork tricks or can change all three in one version. | Product / Cred Ops |
| Q6 | Does the Phase 2 CAQH DEA "hide" (AC-9) mean the block is invisible but still queried, or should the underlying DataRaptor call be skipped too? | Performance vs. traceability trade-off. | Product / Build |
| Q7 | The typo on line 6886 (`LicenseVerifcation` vs `LicenseVerification`) — fold into this story or track separately? | Cleanup scope. | Build team |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|---|---|---|---|
| `PRM_PrimarySourceVerificationReview_English` | OmniScript | **High** | The single OmniScript changed; version 51 → 52 (Post-Go-Live) → 53 (Phase 2). |
| PAR / Initial Cred flow through PSV | Flow | High | Direct — this is the primary consumer. Full regression required. |
| ReCred flow through PSV | Flow | High | Same OmniScript used; save formula on line 7053 is on the ReCred path — regression required. |
| Off-Cycle / RCAT flow | Flow | Medium | Save formula on line 7184 is on the Off-Cycle/RCAT path — regression required. |
| Downstream Case-Close IP chain (consumer of `DEALicenses`) | IP + DR | Medium | Payload shape unchanged; row count may decrease. Regression on `BusinessLicense` (DEA) upsert. |
| QC / Committee / PDA reviewers | Persona / downstream flow | **Positive** | Stop seeing expired DEA data — cleaner review. |
| Sub-OmniScripts `PRM_PSVSubOs*` | OmniScript | None | Not touched. |
| Existing story `PSV_ServiceAreaVerification_CAQHBulkLocation_DataMapper_BugFix_UserStory.md` | Story | None | Different step; no conflict. Can ship in parallel. |

---

## Estimated Effort

*(AI-estimated — validate with the build team.)*

| # | Component | Change Type | Effort | Story Points | Notes |
|---|---|---|---|---|---|
| T1 | License Verification — hide PAR-form license text block | OmniScript element hide | **S** | 1 | One element `showCondition`; single-line change. |
| T4 | DEA Verification — add "all expired" formula + non-blocking warning banner | OmniScript formula + message block | **M** | 3 | New formula element + new message block + `showCondition` wiring. |
| T5 | DEA Verification — filter expired rows out of `DEALicenses` save formula (× 3 paths) | OmniScript save-formula edit | **S** | 2 | Three formula edits (lines 6884 / 7053 / 7184); ensure filter syntax works in the OmniScript formula parser. |
| — | Near-term regression (PAR + ReCred + Off-Cycle) | QA | **M** | 3 | Manual walk-through of each flow to Continue on the DEA step. |
| T2 | Taxonomy Code column | OmniScript verify block edit | **M** | 3 | *Phase 2.* Merge-field path needs Q4 confirmation. |
| T3 | Hide CAQH-specialty column | OmniScript element hide | **S** | 1 | *Phase 2.* |
| T7 | Phase 2 — hide CAQH DEA display block | OmniScript element hide | **S** | 1 | *Phase 2.* |
| — | Phase 2 regression | QA | **M** | 3 | *Phase 2.* |
| — | Deployment (one version per phase) | Config | **S** | 1 | Version activation, permission-set (none new). |

**Rough totals:**
- **Near-term (Post-Go-Live release):** ~S + M + S + M ≈ **~9 story points** — one focused sprint.
- **Phase 2 (Taxonomy + hide CAQH-specialty + hide CAQH DEA + regression):** ~M + S + S + M ≈ **~8 story points**.

---

## Notes for QA / test authoring

For the test case referenced in the QA sandbox (`IndividualApplication` `0iTVB000000Jf4H2AS`, Case `500VB00000hG2Zr`, opened via the [OmniScript launch URL](https://ibx--qa.sandbox.lightning.force.com/lightning/page/omnistudio/omniscript?omniscript__type=PRM&omniscript__subType=PrimarySourceVerificationReview&omniscript__language=English&omniscript__theme=lightning&omniscript__tabIcon=custom%3Acustom18&omniscript__tabLabel=PrimarySourceVerificationReview&c__ContextId=500VB00000hG2Zr&ws=%2Flightning%2Fr%2FIndividualApplication%2F0iTVB000000Jf4H2AS%2Fview)), the tester should capture, for each step, a screenshot of **before** and **after** state and record:

- License step: number of license rows visible, and their source (CAQH vs PAR form).
- Specialty step: whether the taxonomy code column is present, and which specialty rows are visible.
- DEA step: full CAQH DEA payload, their expiration dates, presence/absence of the warning banner, and the resulting `BusinessLicense` (DEA) rows created after clicking Continue.

This pairs with **Group 3** ACs and is what the automated QTA test bridge should target once the story is scheduled.
