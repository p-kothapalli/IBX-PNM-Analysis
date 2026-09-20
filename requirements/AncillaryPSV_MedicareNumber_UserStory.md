# Ancillary PSV — Add Medicare Number on Verify CMS Step (Assessment + Reassessment)

## User Story: Allow Credentialing Specialists to capture newly-discovered Medicare Numbers inline during the Ancillary PSV guided flow, in both the Initial Assessment and Reassessment paths, with consistent validation and persistence on both sides

Document Version: 2.0 — redesigned to use the existing `MedicareMedicaidNumber` Edit Block (`allowNew=true`) for inline add/edit; removed the Yes/No question, separate repeatable block, and custom format/duplicate validation; added the `Pending` → PDA-finalize lifecycle (ref 1135795)
Created: 2026-05-19 · Updated: 2026-06-08
Epic: Ancillary Provider Credentialing — PSV Data Capture Enhancements
Priority: P1 — Business-requested enhancement; closes a data-entry gap surfaced by the Credentialing team
Estimated Effort: M (5–7 dev days + ~2 QA days) — see § 9 breakdown
Vertical: Provider Network Management (PNM) — Independence Blue Cross (IBX)

---

## 1. Executive Summary

Today, during the Ancillary PSV (Primary Source Verification) guided flow,
the Credentialing Specialist can **view** existing Medicare/Medicaid Numbers
already on file for the Ancillary Account (Vendor) but cannot reliably **add
a newly-discovered Medicare Number** through a guided, validated, audited
path on both flows.

- **Initial Assessment** (`PRM_AncillaryPSVForm_English_10`): no add capability
  at all. Specialists must create `Identifier` records manually outside the
  guided flow, which loses the Case Manager / EffectiveFrom audit trail and
  frequently gets missed entirely.
- **Reassessment** (`PRM_AncillaryReassessmentPSV_English_8`): has an add UI
  today via a Yes/No question + separate repeatable block, with full
  back-end persistence (`PRMDRCreateAncReassessPSVIdentifier_1` DR called by
  `PRM_AncillaryReassessmentPSVFormCreation_Procedure_1` IP).

This story brings **both flows to parity** using the **existing
`MedicareMedicaidNumber` Edit Block** as the single capture surface: existing
Medicare Numbers are pre-filled and editable in place, and the Edit Block's
native **+ Add** button adds new rows. The previously-planned Yes/No question,
separate repeatable block, and custom format/duplicate validation are
**dropped** — the Edit Block handles add inline, and per business no custom
Medicare-Number validation is applied beyond the required-field check.
Newly-added Medicare Numbers persist as `Identifier` records stamped
`Pending = TRUE`, and the **Ancillary PDA** step later finalizes them
(`Pending = FALSE`, `Effective From = {HACAC Decision Date}`, `Active`
computed) — see § 7.3.

**Stakeholder decisions (already captured):**

| Decision | Choice |
|----------|--------|
| Scope | **Both flows** — build on Assessment; harden validations on Reassessment |
| Repeat limit | **Up to 10** new Medicare Numbers per PSV submission (both flows) |
| Duplicate guard | **Yes — block submit** if entered Medicare Number matches an existing on-file value or another newly-entered value |
| Format pattern | **Open — see § 10 Q1** |
| Default value of Yes/No question | **Open — see § 10 Q2** |
| Medicaid Number adds | **Out of scope** — Medicare only |

---

## 2. Components Affected

### 2.1 OmniScripts

| OmniScript | Active Version | In-Scope? | Nature of Change |
|------------|---------------|-----------|------------------|
| `PRM_AncillaryPSVForm_English_10` (Assessment) | YES (isActive=true) | **YES** | `VerifyCMS` step: existing `MedicareMedicaidNumber` Edit Block set `allowNew=true`, ID Value child made editable/required, Type + Parent Record read-only pre-filled |
| `PRM_AncillaryReassessmentPSV_English_8` (Reassessment) | YES (isActive=true) | **YES** | `VerifyCMS` step: same Edit Block edits as Assessment; **delete** the Yes/No Radio + separate repeatable block; **repoint** IP/DR new-row binding to the Edit Block |
| `PRM_AncillaryCompletePSVReview_English_1` | YES | **YES (verify only)** | Review screen reads `IdentifierDetails`; confirm rendering of new block items (likely no change) |

### 2.2 Integration Procedures

| IP | In-Scope? | Reason |
|----|-----------|--------|
| `PRM_AncillaryPSVFormCreation_Procedure_2` (Assessment, isActive=true) | **YES** | Add new DR action to invoke `PRMDRCreateAncPSVIdentifier` (new), reading the Edit Block add-rows |
| `PRM_AncillaryReassessmentPSVFormCreation_Procedure_1` (Reassessment) | **YES** | **Repoint** the new-Identifier input from `%VerifyCMS:MedicareNumberNewBlk%` to the Edit Block's add-row data source (block being deleted) |
| Ancillary PDA Review & Update IP/DR (ref **1135795**) | **YES (verify)** | On PDA, update each pending Medicare Identifier: `Pending=FALSE`, `Effective From={HACAC Decision Date}`, `Active` computed |

### 2.3 DataRaptors

| DataRaptor | Type | In-Scope? | Reason |
|-----------|------|-----------|--------|
| `PRMDRAncillaryPSVUpdateIdentifiers_1` (Load) | Existing | NO | Continues to handle UPDATES to existing Identifier records |
| `PRMDRCreateAncPSVIdentifier_1` (Load) | **NEW** | **YES** | Creates new Medicare Number Identifier records; clone of `PRMDRCreateAncReassessPSVIdentifier_1` |
| `PRMDRCreateAncReassessPSVIdentifier_1` (Load) | Existing | NO | Reference implementation — do not modify |

### 2.4 Objects / Fields

| Object | Fields touched | Type of change |
|--------|---------------|---------------|
| `Identifier` (standard) — **on create (PSV completion)** | `IdValue`, `PRM_Type__c` (hardcoded "MCRE"), **`Pending` = TRUE**, `PRM_CaseManager__c`, `ParentRecordId` (= Account Id), `RecordTypeId` (= `PRM_Vendor`) | New records INSERTED (no schema changes) |
| `Identifier` (standard) — **on Ancillary PDA update** | **`Pending` = FALSE**, `PRM_EffectiveFrom__c` (= `{HACAC Decision Date}`), `PRM_Active__c` (computed per § 7.4 AC14) | UPDATED at PDA (ref 1135795) |
| `IndividualApplication` (Case Manager) | None | Read for `Id` linkage |

**No schema changes, no new permission sets** — `Identifier` write is
already granted by `PRM_CredentialingUser`. (Confirm the API name of the
`Pending` field on `Identifier` during implementation.)

### 2.5 Apex / LWC

None. Pure OmniStudio (OmniScript + IP + DR) change.

---

## 3. Current State (from codebase)

### 3.1 Assessment OmniScript `PRM_AncillaryPSVForm_English_10` — `VerifyCMS` step

**Step location:** sequenceNumber **10.0**, file lines ~3217–3568.

| Element | Type | Behavior |
|---------|------|----------|
| `MedicareMedicaidNumber` | Edit Block | Read-only view of existing Medicare/Medicaid Identifiers. `allowNew=false`, `allowDelete=false`, `allowEdit=true` (View More only), `mode=Table`, `maxDisplay=3` |
| `IdentifierIdValue` | Text (child) | Read-only display of `Identifier.IdValue` |
| `IdentifierParentRecord` | Text (child) | Read-only display of parent name |
| `IdentifierType` | Select (child) | Read-only display from `Identifier.PRM_Type__c` |
| `CMSNote` | Text Area | CMS verification notes |
| `CMSReview` | Radio | "Data Looks Good / Not Applicable / Review Needed / Missing Information" |
| `QuickLinkVerifyCMS` | Text Block | Links to qcor.cms.gov and medicare.gov |
| `LineBreak25`, `LineBreak26` | Line Break | Spacers |

**Gap:** No Yes/No question, no add block, no validation, no persistence path
for newly-entered Medicare Numbers.

**Review screen JSON aggregation** (file line 534):

```
"IdentifierDetails" : "%VerifyCMS:MedicareMedicaidNumber%"
```

Currently maps only the existing-records view block.

### 3.2 Reassessment OmniScript `PRM_AncillaryReassessmentPSV_English_8` — `VerifyCMS` step

**Step location:** sequenceNumber **17.0**, file lines ~5982–6596.

| Element | File Line | Current State |
|---------|-----------|---------------|
| `MedicareMedicaidNumber` (Edit Block) | 6263 | Read-only view, shown when `MedicarePresent = true` |
| `MedNumber` (Text, child of view block) | 6148 | Read-only display of existing `Identifier.IdValue` |
| `NewMedicareNumberCheck` (Radio Yes/No) | 6477 | `defaultValue="Yes"`, options `Yes`/`No` |
| `MedicareNumberNewBlk` (Block) | 6446 | `repeat=true`, **`repeatLimit=5`**, shown when `NewMedicareNumberCheck = "Yes"` |
| `IdValueNew` (Text, child) | 6309 | `required=true`, `minLength=0`, `maxLength=255`, **`pattern=""`** (no regex), **`ptrnErrText=""`** (no error), `label="Id Value"`, `controlWidth=4` |
| `IsNewMedActive` (Formula, child) | 6347 | `=MOMENT(%ReAssessmentApplication:DateAssessment%).isSameOrBefore(MOMENT(NOW()))` |
| `ParentRecordNew` (Text, child) | 6371 | `readOnly=true`, `defaultValue="%OrganizationName%"` |
| `TypeMedNew` (Text, child) | 6409 | `readOnly=true`, `defaultValue="Medicare Number"` |

**Gap:** No format/length pattern validation, no duplicate guard, smaller
repeat limit than business now wants, and the field label is generic
("Id Value" instead of "Medicare Number").

**Review screen JSON aggregation** (file line 317):

```
"IdentifierDetails" : "%VerifyCMS:MedicareNumberNewBlk%"
```

Already correct — no change required to the reassessment review mapping.

### 3.3 Reassessment back-end (reference for Assessment build)

**DataRaptor `PRMDRCreateAncReassessPSVIdentifier_1`** (Load, `active=false`,
invoked by IP only) maps:

| Input | Output Field on `Identifier` |
|-------|------------------------------|
| `IdentifierDetails:IdValueNew` | `IdValue` |
| `IdentifierDetails:IsNewMedActive` | `PRM_Active__c` |
| Constant `"MCRE"` | `PRM_Type__c` |
| QUERY `SELECT Id FROM RecordType WHERE SobjectType='Identifier' AND DeveloperName='PRM_Vendor'` | `RecordTypeId` |
| `CaseManagerId` | `PRM_CaseManager__c` |
| `EffectiveFrom` | `PRM_EffectiveFrom__c` |
| `AccountId` | `ParentRecordId` |

**IP call site** in `PRM_AncillaryReassessmentPSVFormCreation_Procedure_1`
(lines 350–378):

```jsonc
{
  "bundle": "PRMDRCreateAncReassessPSVIdentifier",
  "executionConditionalFormula": "ISNOTBLANK(%IdentifierDetails%)",
  "additionalInput": {
    "IdentifierDetails": "=%IdentifierDetails%",
    "AccountId":        "=%AccountId%",
    "EffectiveFrom":    "=%EffectiveFromDate%",
    "CaseManagerId":    "=%PRMDRAncReassesUpdateCaseAndCaseManager:CaseManagerId%"
  }
}
```

### 3.4 Assessment back-end (today)

**IP `PRM_AncillaryPSVFormCreation_Procedure_2`** calls only the UPDATE DR
(lines 398–426):

```jsonc
{
  "bundle": "PRMDRAncillaryPSVUpdateIdentifiers",
  "executionConditionalFormula": "ISNOTBLANK(%IdentifierDetails%)",
  "additionalInput": {
    "IdentifierDetails": "=%IdentifierDetails%"
  }
}
```

No create path exists.

---

## 4. Story

**As a** Credentialing Specialist running an Ancillary PSV (Initial Assessment
or Reassessment),
**I want** to capture one or more newly-discovered Medicare Numbers on the
Verify CMS step of the guided flow, with the same validated, audited
experience as the existing Business License add pattern,
**So that** the PSV record is complete at submission time, the resulting
Identifier records are stamped with my Case Manager ID for audit, and
downstream roster/extract jobs see the correct Medicare Numbers without a
separate out-of-flow data-entry step — regardless of which PSV pathway I am
running.

**Why it matters:** Manual creation of Identifier records outside the PSV
flow is error-prone, bypasses the Case Manager audit link, and frequently
gets missed entirely — leading to incomplete PI / PDM / CAQH extracts and
to follow-up rework loops between Credentialing and Network Management.
Today the Assessment flow lacks the capability entirely, and the
Reassessment flow lacks the validation guardrails — both produce data-quality
drift.

---

## 5. Scope

| Flow | OmniScript | Affected Step | Change Surface |
|------|------------|---------------|----------------|
| Ancillary PSV (Initial Assessment) | `PRM_AncillaryPSVForm_English` | `VerifyCMS` (Step seq 10.0) | **Build:** new OS elements + new DR + new IP step + review-screen JSON update |
| Ancillary Reassessment PSV | `PRM_AncillaryReassessmentPSV_English` | `VerifyCMS` (Step seq 17.0) | **Harden:** property edits on existing elements + new Validation element. Back-end unchanged |
| Ancillary PSV Review (downstream) | `PRM_AncillaryCompletePSVReview_English_1` | Identifier Details summary | Verify rendering (likely no change) |

**Out of scope** (called out so PO/QA are aligned):

1. Editing/deleting existing Medicare Numbers from within the PSV flow (still via PDM Manual Update).
2. Medicaid Numbers — only **Medicare** Number adds are in scope; Medicaid continues to be managed outside this flow.
3. Practitioner PSV (`PRM_PSVSubOsSummary_*`), Off-Cycle, Recred, Initial Cred flows.
4. Permission set changes — `Identifier` write already granted by `PRM_CredentialingUser`.
5. Backfilling already-existing reassessment-created Identifier records that may contain whitespace or punctuation (separate data-fix story if AC7 / AC8 reveals real production hits).
6. Adding a "Cancel pending add" / "Edit before save" capability on entries inside the new block.

---

## 6. Technical Section (For Developers)

### 6.1 Recommended Sequencing

```
                     ┌──────────────────────────────┐
                     │ § 10 Q1 (regex) + Q2 (default)│
                     │ resolved with Credentialing  │
                     │            BA                │
                     └──────────────┬───────────────┘
                                    │
                                    ▼
        ┌───────────────────────────────────────────────────┐
        │ Sub-PR A: Assessment Build                        │
        │   - New OS elements + new DR + new IP step        │
        │   - Locks regex / labels / error messages         │
        └────────────────────┬──────────────────────────────┘
                             │  (merge & deploy)
                             ▼
        ┌───────────────────────────────────────────────────┐
        │ Sub-PR B: Reassessment Hardening                  │
        │   - Lifts Sub-PR A's regex/labels verbatim        │
        │   - Edits OS only — no DR / IP changes            │
        └───────────────────────────────────────────────────┘
```

**Why this order:** the Assessment build locks the regex / labels / error
messages / repeat limit, and the Reassessment hardening lifts those values
verbatim. Running them in parallel risks drift between the two flows — the
exact thing this story exists to prevent.

The two sub-PRs can ship in the same sprint, or back-to-back; the
implementation guide below treats them as one logical change.

### 6.2 Changes Required — Assessment OS (`PRM_AncillaryPSVForm_English_10`)

> **Approach:** modify the existing `MedicareMedicaidNumber` Edit Block in
> place — do **not** add a Radio, a separate repeatable block, or a custom
> Validation element.

| # | Component | Type | Change |
|---|-----------|------|--------|
| A1 | `MedicareMedicaidNumber` (existing Edit Block) | OmniScript property edits | `allowNew`: false → **true** (enables native **+ Add**); `allowEdit` stays **true**; set `repeatLimit`/max new rows = **10**; keep `mode=Table`, `maxDisplay=3` |
| A2 | `IdentifierIdValue` (existing child — ID Value) | OmniScript property edits | Make **editable** (remove read-only); `required=true`; label "Medicare Number" / "ID Value" per UX |
| A3 | `IdentifierType` (existing child — Type) | OmniScript property edit | `readOnly=true`, default "Medicare Number" (pre-populated) |
| A4 | `IdentifierParentRecord` (existing child — Parent Record) | OmniScript property edit | `readOnly=true`, default `{Account Name}` / `%OrganizationName%` (verify binding — see § 6.4 note) |
| A5 | Review screen JSON, line 534 | Edit | Confirm `"IdentifierDetails" : "%VerifyCMS:MedicareMedicaidNumber%"` aggregates both existing + newly-added rows from the Edit Block (no change expected since it already points at the Edit Block) |

> **Removed from prior design:** `NewMedicareNumberCheck` Radio (old A1),
> `MedicareNumberNewBlk` block + children (old A2–A6), and
> `DuplicateMedicareValidation` (old A7). The Edit Block's native add +
> required-field handling replaces them; per business, no custom
> format/duplicate validation is applied.

### 6.3 Changes Required — Reassessment OS (`PRM_AncillaryReassessmentPSV_English_8`)

> **Approach:** same Edit-Block-driven design as Assessment. Today's
> reassessment OS has the Radio + repeatable block **and a wired back-end**
> (`PRMDRCreateAncReassessPSVIdentifier_1` reads
> `%VerifyCMS:MedicareNumberNewBlk%`). Removing the repeatable block means
> the **IP/DR new-row binding must be repointed** to the Edit Block's
> add-row data source — this is the one back-end touch the prior "reassessment
> = no back-end change" assumption no longer holds for.

| # | Component | Type | Change |
|---|-----------|------|--------|
| R1 | `MedicareMedicaidNumber` (existing Edit Block) | OmniScript property edits | `allowNew`: false → **true**; `allowEdit` stays **true**; new-row limit = **10**; keep `show` rule `MedicarePresent=true` only if it should still gate display — **verify** it does not hide the block when there are 0 existing rows (a vendor with no Medicare on file must still be able to **+ Add**) |
| R2 | `MedNumber` (existing child — ID Value) | OmniScript property edits | Make **editable**; `required=true`; label "Medicare Number" |
| R3 | `TypeMed` (existing child — Type) | OmniScript property edit | `readOnly=true`, default "Medicare Number" |
| R4 | `ParentRecordName` (existing child — Parent Record) | OmniScript property edit | `readOnly=true`, default `{Account Name}` |
| R5 | `PRMDRCreateAncReassessPSVIdentifier_1` / `PRM_AncillaryReassessmentPSVFormCreation_Procedure_1` | DR/IP binding edit | **Repoint** the new-Identifier input from `%VerifyCMS:MedicareNumberNewBlk%` to the Edit Block's add-row data source so newly-added rows still persist |
| R6 | `NewMedicareNumberCheck` Radio + `MedicareNumberNewBlk` block | OmniScript element **delete** | Remove the Yes/No question and the separate repeatable block (superseded by R1) |

### 6.4 New DataRaptor — `PRMDRCreateAncPSVIdentifier_1` (Assessment only)

| Item | Value |
|------|-------|
| Type | Load |
| Source Object | `json` |
| Output Object | `Identifier` |
| Active | `false` (invoked via IP only — matches reassessment convention) |
| Unique Name | `PRMDRCreateAncPSVIdentifier_1` |
| Name | `PRMDRCreateAncPSVIdentifier` |

Field mapping (clone of `PRMDRCreateAncReassessPSVIdentifier_1`):

| Input Path | Output Field | Notes |
|-----------|--------------|-------|
| Formula `QUERY("SELECT Id FROM RecordType WHERE SobjectType='Identifier' AND DeveloperName='PRM_Vendor'")` → `vendorRecTypeId` | `RecordTypeId` | Same as reassessment |
| Constant `"MCRE"` | `PRM_Type__c` | Hard-coded — Medicare only per § 5 |
| `IdentifierDetails:IsNewMedActive` | `PRM_Active__c` | Driven by formula A6 |
| `CaseManagerId` | `PRM_CaseManager__c` | Passed from IP |
| `EffectiveFrom` | `PRM_EffectiveFrom__c` | Passed from IP — Assessment date or `TODAY()` per § 10 Q3 |
| `AccountId` | `ParentRecordId` | Passed from IP, sourced from `%VerifyAttestationSignature:AccountId%` |
| `IdentifierDetails:IdValueNew` | `IdValue` | The user-entered Medicare Number |

### 6.5 IP Step Add — `PRM_AncillaryPSVFormCreation_Procedure_2` (Assessment only)

Insert a new DR action **after** the existing `PRMDRAncillaryPSVUpdateIdentifiers`
step (so updates run first):

```jsonc
{
  "bundle": "PRMDRCreateAncPSVIdentifier",
  "executionConditionalFormula": "ISNOTBLANK(%IdentifierDetails%)",
  "useFormulas": true,
  "sendOnlyAdditionalInput": true,
  "additionalInput": {
    "IdentifierDetails": "=%IdentifierDetails%",
    "AccountId":        "=%AccountId%",
    "EffectiveFrom":    "=%EffectiveFromDate%",
    "CaseManagerId":    "=%PRMDRAncillaryPSVUpdateCaseAndCaseManager:CaseManagerId%"
  }
}
```

> **Note:** verify the exact name of the case-manager DR action in the
> assessment IP — reassessment uses `PRMDRAncReassesUpdateCaseAndCaseManager`;
> the assessment-side equivalent must be discovered during implementation
> (likely `PRMDRAncillaryPSVUpdateCaseAndCaseManager` or
> `PRMDRTCaseManagerDetailsAncillaryComplete`).

### 6.6 Duplicate-Guard Validation Specification (both flows) — SUPERSEDED

> **SUPERSEDED by the updated design.** Per business ("remove validation for
> Medicare number") and because the Edit Block handles add inline, **no
> step-level duplicate-guard Validation element is built**. The original
> specification is retained below for historical context only and should
> **not** be implemented.

Add a step-level `Validation` element that fires when **any** newly-entered
`IdValueNew` matches **any** existing `Identifier.IdValue` on the read-only
view block for the same Account, OR matches another newly-entered value
(intra-form duplicate).

Proposed OmniStudio formula:

```
=IFERROR(
  LEN(
    INTERSECT(
      UPPER(LIST(%VerifyCMS:MedicareNumberNewBlk:IdValueNew%)),
      UPPER(LIST(%VerifyCMS:MedicareMedicaidNumber:<child>%))
    )
  ) > 0,
  false
)
```

**Critical:** the `<child>` placeholder differs between flows:

| Flow | Existing-numbers child element |
|------|--------------------------------|
| Assessment | `IdentifierIdValue` (line 3353) |
| Reassessment | `MedNumber` (line 6148) |

**Implementation pattern reference:** `PreciselySkipMessage` Validation
element on the `AddressValidation` step of the same reassessment OS (lines
49–82) demonstrates the `validateExpression` + `messages[]` + `type=Validation`
structure to mirror.

If the OmniStudio formula engine cannot perform `INTERSECT(LIST(...), LIST(...))`
natively, the fallback is a **custom LWC validator** (cf. `prmAdditionalAddressValidation`)
or a **server-side DataRaptor Extract** returning a match count used as the
validation source. Confirm approach at implementation kickoff. The same
fallback applies identically to both flows.

**Error message (both flows):** *"One or more Medicare Numbers you entered
are already on file for this Ancillary provider. Please remove duplicates
before proceeding."*

### 6.7 Field-Level Validations on the ID Value field (both flows) — SUPERSEDED

> **SUPERSEDED by the updated design.** Per business ("remove validation for
> Medicare number"), the only validation retained is the Edit Block's native
> **required** check on the ID Value child field (AC6). No custom
> pattern/min/max/whitespace/uppercase rules are applied. The table below is
> retained for historical context only.

| Validation | Rule | Error Message |
|-----------|------|---------------|
| Required | `required=true` | "Medicare Number is required." |
| Min length | `minLength=1` | "Medicare Number cannot be blank." |
| Max length | `maxLength=20` (safe upper bound; covers CCN, PTAN, MBI, and future CMS IDs) | "Medicare Number cannot exceed 20 characters." |
| Pattern | **TBD — see § 10 Q1** — default proposal: `^[A-Za-z0-9]{1,20}$` | "Medicare Number must contain letters and digits only — no spaces or special characters." |
| Whitespace trim | OS-level — values trimmed before validation | n/a |
| Uppercase normalize | OS-level (if supported) | n/a |

### 6.8 Reference Files (do NOT modify)

| File | Use As |
|------|--------|
| `force-app/main/default/omniScripts/PRM_AncillaryReassessmentPSV_English_8.os-meta.xml` lines 6263–6595 | OmniScript element template for Assessment build (A1–A7) |
| `force-app/main/default/omniDataTransforms/PRMDRCreateAncReassessPSVIdentifier_1.rpt-meta.xml` | DataRaptor template for new `PRMDRCreateAncPSVIdentifier_1` |
| `force-app/main/default/omniIntegrationProcedures/PRM_AncillaryReassessmentPSVFormCreation_Procedure_1.oip-meta.xml` lines 350–378 | IP step template for IP edit |
| Same reassessment OS, lines 49–82 (`PreciselySkipMessage`) | `Validation` element XML structure reference for duplicate-guard (A7 + R3) |

---

## 7. Acceptance Criteria

> **Design (updated):** The "Do you want to add a new Medicare Number?"
> Yes/No question and the separate repeatable `MedicareNumberNewBlk` block
> are **removed**. Both flows now use the existing `MedicareMedicaidNumber`
> **Edit Block** (Table mode) with `allowNew=true` so its native **+ Add**
> button drives adding a new Medicare Number row, and existing rows are
> pre-filled and editable in place. Validation is handled natively by the
> Edit Block / OmniScript — no custom format/duplicate validation element
> (see § 6.6 / § 6.7, now superseded). Both flows behave identically
> ("Same as Ancillary Re-Assessment").

ACs are sectioned by concern and apply to **both flows**
(`PRM_AncillaryPSVForm_English` and `PRM_AncillaryReassessmentPSV_English`)
unless noted. Numbering is shared so test-matrix mapping in § 13 is
unambiguous.

### 7.1 Verify CMS — UI / OmniScript Behavior (both flows)

| # | Given | When | Then |
|---|-------|------|------|
| AC1 | Credentialing Specialist is on the Verify CMS step for an Ancillary Vendor | They view the page | `MedicareMedicaidNumber` Edit Block (Table mode) renders, **pre-filled with the existing Medicare Numbers on file**; rows are editable; a native **+ Add** action is available (`allowNew=true`). No Yes/No question is shown |
| AC2 | User does not add or edit any row | They click Next | No new Identifier created; existing rows unchanged; step validation fires normally |
| AC3 | User clicks **+ Add** | New row form opens | Fields shown: **ID Value** (editable, required), **Type** = "Medicare Number" (read-only, pre-populated), **Parent Record** = `{Account Name}` (read-only, pre-populated) |
| AC4 | User adds rows via **+ Add** | They click **+ Add** repeatedly | Up to **10** new rows can be added; 11th **+ Add** disabled / no-op |
| AC5 | User enters an ID Value on a new row | They click **Save** on the row | New row displays in the Edit Block table |
| AC6 | User leaves ID Value blank on a new row | They Save the row / click Next | Edit Block required-field validation blocks Save/advance |
| AC7 | User enters any Medicare Number value | They Save / click Next | Value accepted — **no custom format or duplicate validation** is applied (validation handled natively by the Edit Block; per business "remove validation for Medicare number") |
| AC8 | User edits an existing pre-filled row | They Save the row | Edited value retained in the table and persisted via the existing Identifier update path |

### 7.2 Persistence — Upon Flow Completion (both flows)

| # | Given | When | Then |
|---|-------|------|------|
| AC9 | User completes the flow with 1–10 new Medicare Numbers | Flow completion / creation IP runs | One **Identifier** record created per new entry: `ID Value` = `{ID Value}`, `Type` = "Medicare Number" (`PRM_Type__c` = "MCRE"), `Parent Record` = `{Account}` (`ParentRecordId` = Account Id), **`Pending` = TRUE**, `Case Manager` = `{Case Manager}` (`PRM_CaseManager__c`), `RecordTypeId` = `PRM_Vendor` |
| AC10 | User completes the flow with no new entries | IP runs | No new Identifier created; existing-update path runs as today |
| AC11 | User completes with both edits to existing rows and new rows | IP runs | Both update + create actions complete in a single IP execution; no race condition |
| AC12 | DR insert fails for one row (DML, FLS, governor) | IP runs | OmniStudio default error surfaced; partial-success behavior matches reassessment (`rollbackOnError=false` mirrored) — see § 10 Q4 |

### 7.3 Lifecycle — Upon Ancillary PDA (both flows)

> Cross-referenced with **1135795 — Ancillary - PDA Review & Update -
> Records Update (2)** (Closed).

| # | Given | When | Then |
|---|-------|------|------|
| AC13 | A Medicare Number Identifier was created with `Pending = TRUE` | The Ancillary PDA Review & Update runs for the case | The Identifier is updated: `Record Type` = Vendor Identifier (Medicare Number), **`Pending` = FALSE**, **`Effective From` = `{HACAC Decision Date}`** |
| AC14 | PDA update sets the `Active` flag | `Active` is evaluated | `Active` = **TRUE** if `Effective From <= TODAY` AND `Effective To > TODAY`; if `Effective To = Null` then `Active` = **TRUE** if `Effective From <= TODAY`; **else FALSE** |

### 7.4 Cross-Cutting — Review & Regression

| # | Given | When | Then |
|---|-------|------|------|
| AC15 | (Either flow) User completes PSV with new Medicare Numbers | They (or another user) opens the Complete PSV Review OS | IdentifierDetails section shows the new entries |
| AC16 | (Either flow) Same scenario | Bell notification / Case Note fires | Notification body / Case Note records the count of new Medicare Numbers added (optional — see § 10 Q5) |
| AC17 | Existing in-flight Case in `In Progress` created **before** deploy | User resumes the PSV after deploy | Verify CMS step loads cleanly; existing Medicare rows pre-fill in the Edit Block; **+ Add** available; no script error from the removed Radio/Block bindings |
| AC18 | (Out-of-scope flows) Practitioner / Off-Cycle / Recred PSV | Run end-to-end | Zero change — both edits are isolated to Ancillary OmniScripts |
| AC19 | Vendor with 0 existing Medicare Numbers adds 3 new ones | After completion | Edit Block (and downstream PDM/PI extracts) shows all 3 on subsequent visits |

---

## 8. Implementation Sub-PR Breakdown (Recommended)

For reviewability, ship in two sub-PRs against the same story. Both can be
in the same sprint.

| Sub-PR | Content | ACs Covered | Effort |
|--------|---------|-------------|--------|
| **A: Assessment** | Edit Block edits A1–A4 (allowNew, editable ID Value, RO Type/Parent), new DR (§ 6.4), IP step add (§ 6.5), review-screen verify (A5) | AC1–AC12, AC15–AC19 | S–M (2–3 dev days + ~1 QA day) |
| **B: Reassessment** | Edit Block edits R1–R4, **delete** Radio + repeatable block (R6), **repoint** IP/DR new-row binding (R5) | AC1–AC12, AC15–AC19 (reassessment runs) + AC17 in-flight resume | S–M (2–3 dev days + ~1 QA day) |
| **C: PDA finalization** | Verify/implement Ancillary PDA update of pending Medicare Identifiers (`Pending=FALSE`, `Effective From`, `Active`) — ref 1135795 | AC13, AC14 | S (verify-first; may already exist via 1135795) |

Sub-PR B repoints the reassessment back-end binding (the separate repeatable
block is removed), so it carries a back-end change the prior plan did not.

---

## 9. Estimated Effort

> AI-estimated — validate with the OmniStudio development team during sprint planning.

### 9.1 Sub-PR A — Assessment Build

| Component | Effort | Notes |
|-----------|--------|-------|
| OS element additions A1–A7 (Radio + Block + 4 children + Validation) | **M (4–6 hrs)** | Mostly mechanical clone of reassessment OS pattern |
| A8: Review screen JSON mapping update | **S (< 1 hr)** | One-line change at file line 534 |
| New `PRMDRCreateAncPSVIdentifier_1` DR | **M (2–4 hrs)** | Clone of `PRMDRCreateAncReassessPSVIdentifier_1` with new uniqueName |
| IP `PRM_AncillaryPSVFormCreation_Procedure_2` new step | **M (2–4 hrs)** | New DR action; verify case-manager element binding |
| Duplicate-guard fallback (custom LWC or DR Extract) | **M (2–4 hrs)** | Only if § 6.6 formula approach fails |
| QA — manual UAT for AC1–AC16, AC28–AC31 | **L (1–1.5 days)** | 20 ACs, includes deploy-then-resume regression in AC30 |

**Sub-PR A subtotal: M (3–5 dev days + ~1.5 QA days)**

### 9.2 Sub-PR B — Reassessment Hardening

| Component | Effort | Notes |
|-----------|--------|-------|
| R1: `IdValueNew` property edits (label, widths, lengths, regex, error text) | **S (< 1 hr)** | 6 properties on one element |
| R2: `MedicareNumberNewBlk` `repeatLimit` change | **S (< 30 min)** | One property |
| R3: New step-level Validation element | **S (< 1 hr)** | Lift Sub-PR A's structure verbatim, change child element name to `MedNumber` |
| R4 (optional): `NewMedicareNumberCheck` default flip | **S (< 30 min)** | Skip if § 10 Q2 keeps "Yes" |
| R5: Whitespace/uppercase normalization | **S–M (1–3 hrs)** | Depends on OmniStudio formula support; same approach as Sub-PR A |
| QA — manual UAT for AC17–AC27, AC32 | **M (4–6 hrs)** | 12 ACs; back-end unchanged |

**Sub-PR B subtotal: S–M (1.5–2.5 dev days + ~0.5 QA day)**

### 9.3 Total

**Total Estimated Effort: M (5–7 dev days + ~2 QA days).** Single
OmniStudio developer + QA can complete in one sprint.

---

## 10. Clarification Questions (Before Implementation)

| # | Question | Impact | Owner | Default if no answer |
|---|----------|--------|-------|----------------------|
| Q1 | ~~Final regex / format for the Medicare Number?~~ **RESOLVED — moot.** Per business ("remove validation for Medicare number"), no format/pattern validation is applied; only the Edit Block required-field check remains. | n/a | — | No validation |
| Q2 | ~~Default value of the Yes/No question?~~ **RESOLVED — moot.** The Yes/No question is removed; the Edit Block's **+ Add** drives adding rows. | n/a | — | Question removed |
| Q3 | `PRM_EffectiveFrom__c` source on the new Identifier: (a) `TODAY()`, (b) Assessment date captured on the case, (c) user-entered field. Reassessment uses Reassessment Application date. | Audit / extract accuracy | Credentialing BA | (b) Assessment date if bound in OS context; else (a) `TODAY()` |
| Q4 | If one of N new inserts fails, (a) roll back the whole PSV submission or (b) save successful ones and surface partial error? Reassessment today is (b). | Data consistency vs. UX | Engineering + PO | (b) Partial save — match reassessment |
| Q5 | Should a Case Note / bell notification record the count of newly-added Medicare Numbers? | Audit-trail visibility | PO | Yes — appended to existing PSV Notes (AC29) |
| Q6 | When duplicate-guard fires, show the conflicting value(s) in the error message, or generic message only? | UX | UX | Generic message (avoids exposing IDs in toasts) |
| Q7 | Are there scenarios where Medicaid Numbers also need to be added in the same UX (today's view block is labelled "Medicare/Medicaid Number")? | Scope — could double the work | Credentialing BA | No — Medicare only |
| Q8 | Backfill / scrub of already-existing reassessment-created Identifier records that may contain whitespace or punctuation? | Data hygiene | Data Team | Out of scope — separate data-fix story if AC21/AC22 reveals real production hits |

---

## 11. Decision Log (Already Resolved)

| # | Question | Decision | Date |
|---|----------|----------|------|
| D1 | Repeat limit for new Medicare Numbers | **10** in both flows (above today's reassessment 5) | 2026-05-19 |
| D2 | Duplicate guard — block on duplicates with existing on-file values | **Yes** (step-level Validation) | 2026-05-19 |
| D3 | Scope — both flows or just Assessment? | **Both** — build Assessment, harden Reassessment | 2026-05-19 |
| D4 | Reassessment back-end changes? | **No** — DR + IP already work end-to-end | 2026-05-19 |
| D5 | Medicaid scope? | **No** — Medicare only | 2026-05-19 |
| D6 | UX paradigm | Mirror existing Business License "Add new" pattern (which the reassessment Medicare add itself mirrors) | 2026-05-19 |

---

## 12. Risks

1. **OmniStudio formula INTERSECT limitation.** Both flows rely on the same
   duplicate-guard formula (§ 6.6). If the OS engine can't perform the
   intersect natively, both need the same fallback (custom LWC validator
   or server-side DR Extract). Solve once in Sub-PR A and reuse.
2. **Element-name binding mismatch between flows.** Assessment uses
   `IdentifierIdValue` for the read-only Identifier-table child; Reassessment
   uses `MedNumber`. § 6.6 + R3 call this out so the dup-guard formula uses
   the correct binding per flow.
3. **Case Manager element binding mismatch.** The reassessment IP references
   `%PRMDRAncReassesUpdateCaseAndCaseManager:CaseManagerId%`; the assessment
   IP has its own equivalent that must be discovered during § 6.5
   implementation. If the assessment IP does not surface Case Manager Id in
   the same step, a new DR Extract may be required.
4. **Reassessment back-end repoint (R5).** Deleting the
   `MedicareNumberNewBlk` repeatable block breaks the existing IP/DR input
   `%VerifyCMS:MedicareNumberNewBlk%`. The new-Identifier binding **must** be
   repointed to the Edit Block's add-row source or new adds silently stop
   persisting. TC-21 guards this.
5. **In-flight cases at deploy time.** The Edit Block already exists in both
   OS, so resumed cases pre-fill existing rows and gain **+ Add** cleanly;
   risk is only stale references to the removed Radio/Block in saved JSON.
   AC17 / TC-18 verify.
6. **No Medicaid path.** Hard-coded `PRM_Type__c = "MCRE"` is intentional;
   if business reverses on § 10 Q7, this becomes a downstream change to
   the new DR + both Edit Blocks (add an editable "Type" child field).
7. **No validation per business.** With format/duplicate validation removed,
   malformed or duplicate Medicare Numbers can be saved. This is an accepted
   business decision ("remove validation for Medicare number"); only the
   Edit Block's required-field check on ID Value remains.
8. **`Pending` field API name.** AC9/AC13 depend on the `Pending` field on
   `Identifier`; confirm its exact API name and that both the create DR and
   the PDA update (1135795) write it consistently.

---

## 13. Test Matrix (UAT Checklist)

One row per AC. Includes both flows + cross-cutting + sandbox-only
regression cases.

| TC | AC | Flow | Description |
|----|----|------|-------------|
| TC-01 | AC1 | Both | Verify CMS shows the `MedicareMedicaidNumber` Edit Block pre-filled with existing Medicare Numbers; **+ Add** available; no Yes/No question |
| TC-02 | AC1 | Both | Vendor with 0 existing Medicare Numbers → Edit Block still renders with **+ Add** available |
| TC-03 | AC2 | Both | Don't add/edit anything → click Next → succeeds, no new Identifier |
| TC-04 | AC3 | Both | Click **+ Add** → new row form shows ID Value (editable), Type "Medicare Number" (RO), Parent Record {Account} (RO) |
| TC-05 | AC4 | Both | Add 1, 5, 10 rows; 11th **+ Add** disabled / no-op |
| TC-06 | AC5 | Both | Enter an ID Value, Save row → new row displays in the table |
| TC-07 | AC6 | Both | Leave ID Value blank on a new row → required-field validation blocks Save/Next |
| TC-08 | AC7 | Both | Enter value with space / punctuation / 21+ chars → accepted (no custom format/length/dup validation) |
| TC-09 | AC8 | Both | Edit an existing pre-filled row, Save → edited value retained + persisted via update path |
| TC-10 | AC9 | Both | Complete flow with 3 new values → verify `Identifier` records: Type=MCRE, ParentRecordId=Account, RecordTypeId=PRM_Vendor, CaseManager set, **Pending=TRUE** |
| TC-11 | AC10 | Both | Complete with no new entries → no new Identifier; existing-update path still works |
| TC-12 | AC11 | Both | Complete with mix of edit-existing + add-new in one submission → both complete |
| TC-13 | AC12 | Both | Force DML failure on one row → verify partial-save behavior |
| TC-14 | AC13 | Both (PDA) | Run Ancillary PDA → pending Medicare Identifier updated: Pending=FALSE, Effective From={HACAC Decision Date}, RecordType=Vendor Identifier (Medicare Number) |
| TC-15 | AC14 | Both (PDA) | Verify `Active` computed correctly across the date-boundary cases (Effective To set, null, future, past) |
| TC-16 | AC15 | Both | After completion, open Complete PSV Review → IdentifierDetails shows the new entries |
| TC-17 | AC16 | Both | Per § 10 Q5 decision: verify Case Note / bell notification mentions count of new entries |
| TC-18 | AC17 | Both | Resume `In Progress` case created before deploy → Edit Block pre-fills, **+ Add** present, no script error from removed Radio/Block |
| TC-19 | AC18 | Out-of-scope | Spot-check Practitioner / Off-Cycle / Recred PSV flows → zero behavior change |
| TC-20 | AC19 | Both | Vendor with 0 existing, add 3 new → re-open case → all 3 show in the Edit Block |
| TC-21 | AC9 | Reassessment | After R5 repoint, confirm added rows persist (Identifier created) — guards against the removed-block binding break |
| TC-22 | n/a | Both | Permission check — run as `PRM_CredentialingUser` → add + persistence work |
| TC-23 | n/a | Both | Performance — add 10 new Medicare Numbers → runtime within normal IP envelope |

---

## 14. Definition of Done

- [ ] `Pending` field API name on `Identifier` confirmed (Q3 — Effective From source) resolved with Credentialing BA
- [ ] Sub-PR A merged: Assessment Edit Block edits A1–A4, new `PRMDRCreateAncPSVIdentifier_1` DR, IP step in `PRM_AncillaryPSVFormCreation_Procedure_2`
- [ ] Sub-PR B merged: Reassessment Edit Block edits R1–R4, Radio + repeatable block deleted (R6), IP/DR new-row binding repointed (R5)
- [ ] Sub-PR C verified: Ancillary PDA finalizes pending Medicare Identifiers (Pending=FALSE, Effective From, Active) — ref 1135795
- [ ] Review screen JSON mapping verified to aggregate Edit Block existing + new rows (A5)
- [ ] All acceptance criteria (AC1–AC19) pass in QA sandbox (test matrix § 13: 23 TCs)
- [ ] No regression on the other PSV flows (TC-19)
- [ ] Reassessment add still persists after the back-end repoint (TC-21)
- [ ] Remaining Clarification Questions (Q3–Q8) resolved or explicitly accepted as defaults
- [ ] Release notes include: (a) Verify CMS now lets users add Medicare Numbers directly in the Edit Block (no Yes/No question); (b) reassessment back-end binding repointed off the removed repeatable block
- [ ] Deployed to UAT and signed off by Credentialing Product Owner

---

## 15. Cross-Cutting Owners

| Role | Responsibility |
|------|---------------|
| Product Owner | Approve story; resolve Q1 / Q2 / Q5 / Q7; UAT signoff |
| Credentialing BA / Compliance | Provide regex + Medicare format expectations (Q1); confirm Q3, Q7 |
| UX / Credentialing Lead | Q2 (default), Q6 (error message style) |
| OmniStudio Developer | Implement Sub-PR A + B (single developer can cover both) |
| QA | Execute § 13 test matrix |
| Release | Deploy via `./TEST_DEPLOYMENT_COMMANDS.sh`; include release notes per § 14 |

---

## 16. Related / Cross-Reference

- `requirements/PSV_Review_LWC_Redesign_Detailed_Design.md` — adjacent area; downstream review screen design. No direct dependency.
- `requirements/QC_Edit_Mode_Build_Spec.md` — downstream of PSV; will display new Identifier records via existing QC read paths. No change.
- Reference impl (do not modify): `force-app/main/default/omniScripts/PRM_AncillaryReassessmentPSV_English_8.os-meta.xml` (`VerifyCMS` step, lines 6263–6595)
- Reference impl (do not modify): `force-app/main/default/omniDataTransforms/PRMDRCreateAncReassessPSVIdentifier_1.rpt-meta.xml`
- Reference impl (do not modify): `force-app/main/default/omniIntegrationProcedures/PRM_AncillaryReassessmentPSVFormCreation_Procedure_1.oip-meta.xml` (lines 350–378)
- Files to edit: `force-app/main/default/omniScripts/PRM_AncillaryPSVForm_English_10.os-meta.xml` (Sub-PR A), `force-app/main/default/omniScripts/PRM_AncillaryReassessmentPSV_English_8.os-meta.xml` (Sub-PR B), `force-app/main/default/omniIntegrationProcedures/PRM_AncillaryPSVFormCreation_Procedure_2.oip-meta.xml` (Sub-PR A)
- File to create: `force-app/main/default/omniDataTransforms/PRMDRCreateAncPSVIdentifier_1.rpt-meta.xml` (Sub-PR A)

---

## Appendix A — Element Tree on `VerifyCMS` Step (After Change)

> **Updated design:** No Yes/No Radio, no separate repeatable block, no
> custom Validation element. The existing `MedicareMedicaidNumber` Edit Block
> is flipped to `allowNew=true` and its child fields are made
> editable (ID Value) / read-only-prefilled (Type, Parent Record), so the
> Edit Block's native **+ Add** drives the create path and its native
> required-field handling covers validation.

### A.1 Assessment (`PRM_AncillaryPSVForm_English_10`)

```
VerifyCMS (Step, seq 10.0)
├── QuickLinkVerifyCMS (Text Block)                       — existing
├── MedicareMedicaidNumber (Edit Block, Table)            — EDITED: allowNew=false → TRUE,
│   │                                                       repeatLimit=10, editLabel kept,
│   │                                                       child fields editable per below
│   ├── IdentifierIdValue   (Text)     ← ID Value, editable + required   — EDITED
│   ├── IdentifierType      (Select/Text) ← Type "Medicare Number", RO   — existing
│   └── IdentifierParentRecord (Text)  ← Parent Record {Account}, RO     — existing
├── LineBreak25 (Line Break)                              — existing
├── LineBreak26 (Line Break)                              — existing
├── CMSReview (Radio)                                     — existing
└── CMSNote   (Text Area)                                 — existing
```

*(Removed vs. prior design: `NewMedicareNumberCheck` Radio,
`MedicareNumberNewBlk` repeatable block + its children, and
`DuplicateMedicareValidation`.)*

### A.2 Reassessment (`PRM_AncillaryReassessmentPSV_English_8`)

```
VerifyCMS (Step, seq 17.0)
├── TextBlock2 / QuickLinkCMS (Text Block)                — existing
├── MedicareMedicaidNumber (Edit Block, Table)            — EDITED: allowNew=false → TRUE,
│   │                                                       repeatLimit=10, child fields
│   │                                                       editable per below
│   │                                                       [shown when MedicarePresent=true]
│   ├── MedNumber           (Text)     ← ID Value, editable + required   — EDITED
│   ├── TypeMed             (Select/Text) ← Type "Medicare Number", RO   — existing
│   └── ParentRecordName    (Text)     ← Parent Record {Account}, RO     — existing
└── (no Radio / repeatable block / Validation)
```

*(Removed vs. today's reassessment OS: `NewMedicareNumberCheck` Radio and
the separate `MedicareNumberNewBlk` repeatable block + children. **Note the
back-end binding implication** — see § 6.3 R-series: the IP/DR that today
read `%VerifyCMS:MedicareNumberNewBlk%` must be repointed to the Edit Block's
new-row data source.)*
