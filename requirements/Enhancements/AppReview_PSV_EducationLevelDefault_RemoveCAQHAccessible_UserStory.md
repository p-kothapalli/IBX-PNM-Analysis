# USER STORY: Default Education Level to "Professional School" and Remove "CAQH Accessible" from the PPR Case View

**Persona:** Credentialing Specialist (Application Review & PSV Education Verification)
**Priority:** P2 (UX / data-quality enhancement)
**Vertical:** Provider Network Management (PNM)
**OmniScript:** `PRM_CredApplicationReviewSubOS_English` (App Review sub-OS, embedded in `PRM_InitialCredentialAppReview`), `PRM_PSVSubOsWSNPDB_English` (PSV Education Verification sub-OS)
**Integration Procedures:** N/A (no IP change)
**Layout:** `IndividualApplication – Practitioner Participation Request Layout`
**Relevant Requirements:** `requirements/PersonEducation_Empty_Fields_Root_Cause_Analysis.md` (institution dropdown / required-field hardening), `requirements/SOQL/2026-06-23_CaseManagersMissingInstitution.md`, `requirements/SOQL/2026-06-05_PARFormPersonEducationMissingInstitution.md`

---

## Story

**As a** Credentialing Specialist,
**I want** the Education Level field in the Application Review and PSV Education Verification education steps to pre-fill with the value CAQH returns, and to fall back to "Professional School" only when CAQH provides no education type — and the "CAQH Accessible" indicator removed from my Practitioner Participation Request case view,
**So that** I capture education records faster and more consistently, with the CAQH-sourced value honored when available, and I'm not distracted by an internal CAQH flag that isn't part of my verification task.

**Why it matters:** Following the recent change that forces specialists to pick the Institution from a dropdown, the team wants to further reduce manual data entry and rework on the education step. When CAQH returns an education type, that value should be respected; only when CAQH has nothing should the field default to "Professional School" (the most common case), reducing missing/blank Education Level values. Separately, the read-only "CAQH Accessible" field on the PPR case view adds noise for the credentialing specialist and is not needed for the participation-request review.

---

## Scope

| Flow | OmniScript / Layout | Affected Step / Element | Data Source |
|------|---------------------|-------------------------|-------------|
| Application Review (Initial Cred) | `PRM_CredApplicationReviewSubOS_English` | `EducationLevelSF` (in `CAQHPersonEducation` block), `VerifyEducationLevel` (in `PersonEducationPractitioner` block) | Picklist `PersonEducation.EducationLevel` |
| PSV Education Verification | `PRM_PSVSubOsWSNPDB_English` | `EducationLevelSF` (in `CAQHPersonEducation` block), `VerifyEducationLevel` (in `PersonEducationBlock` block) | Picklist `PersonEducation.EducationLevel` |
| Practitioner Participation Request case view | `IndividualApplication – Practitioner Participation Request Layout` | `PRM_CAQHAccessible__c` layout item (Readonly) | IndividualApplication field |

---

## Current State (from codebase)

### `PRM_CredApplicationReviewSubOS_English` (App Review sub-OS)

- **`EducationLevelSF`** (Select): label "Education Level", parent edit block `CAQHPersonEducation`, `optionSource = PersonEducation.EducationLevel`, `required: true`, **`defaultValue: null`**.
- **`VerifyEducationLevel`** (Select): label "Education Level", parent edit block `PersonEducationPractitioner`, `optionSource = PersonEducation.EducationLevel`, `required: true`, **no `defaultValue` key (effectively blank)**.

### `PRM_PSVSubOsWSNPDB_English` (PSV Education Verification sub-OS)

- **`EducationLevelSF`** (Select): label "Education Level", parent edit block `CAQHPersonEducation`, `optionSource = PersonEducation.EducationLevel`, `required: true`, **`defaultValue: null`**, shown when `CaseType <> "QC Review"`.
- **`VerifyEducationLevel`** (Select): label "Education Level", parent edit block `PersonEducationBlock`, `optionSource = PersonEducation.EducationLevel`, `required: true`, **no `defaultValue` key**, shown when `CaseType <> "QC Review"`.

### CAQH education data flow into `EducationLevelSF` (verified)

CAQH returns an **`EducationTypeName`** for each education record. This single API field spans **both** the CAQH "Education Type" value set **and** the CAQH "Training Type" value set, and whatever value comes back is used to pre-fill the Education Level field. Known CAQH values (from business screenshots):

- **Education Type:** Undergraduate, Professional School, Fifth Pathway
- **Training Type:** Internship, Residency, Fellowship, Other Training, Faculty Positions / Academic Appointments

The `EducationLevelSF` field in the CAQH block is fed from that value:

- **`PRMDRTCAQHPersonEducation`** (DataMapper): maps `CAQHEducation:EducationTypeName` → `CAQHEducation:EducationLevelSF` — a **direct copy with no value translation**.
- **`PRMCAQHReviewTransform`** (DataMapper): formula `EducationLevelFinal = IF(ISNOTBLANK(PractitionerForm:PractitionerDegree:EducationLevel), PractitionerForm:PractitionerDegree:EducationLevel, Provider:ValidatedEducation:EducationTypeName)` → output `VerifyEducation:CAQHPersonEducation:EducationLevelSF`.

**Implication:** when CAQH supplies an education/training type, `EducationLevelSF` is already pre-filled; when CAQH supplies nothing, the bound node is empty. An OmniStudio `defaultValue` applies **only to an empty node**, so setting `defaultValue = "Professional School"` produces the desired "pre-fill from CAQH, else default" behavior **without** overwriting CAQH values.

**Mapping gap (risk):** because the copy is direct (no value translation), any CAQH `EducationTypeName` that is not an exact `PersonEducation.EducationLevel` picklist value will not render as a selected option. Comparing the known CAQH values to the live picklist:

| CAQH `EducationTypeName` | Matches a picklist value? |
|---|---|
| Undergraduate | ✅ Yes |
| Professional School | ✅ Yes |
| Internship | ✅ Yes |
| Residency | ✅ Yes |
| Fellowship | ✅ Yes |
| **Fifth Pathway** | ❌ No |
| **Other Training** | ❌ No (picklist has `Training`, not `Other Training`) |
| **Faculty Positions / Academic Appointments** | ❌ No |

The three unmatched values (and any other CAQH value not in the picklist) need a mapping decision (see Clarification Q6/Q7) so they don't land on the Select with no matching option.

### `PersonEducation.EducationLevel` picklist (verified live in org `IBXQA`)

- Active values include: `Additional Years`, `Chiropractic School`, `Dental School`, `Fellowship`, `Graduate`, `Internship`, `Medical School`, `Optometry School`, `Podiatry School`, `Post Doctoral`, `Postgraduate`, `Preceptorship`, **`Professional School`**, `Residency`, `Sleep Medicine Program`, `Training`, `Undergraduate`.
- **`Professional School`** is an active value — exact string to use for the default.

### `IndividualApplication – Practitioner Participation Request Layout`

- Contains a layout item **`PRM_CAQHAccessible__c`** (label "CAQH Accessible") with behavior **Readonly**.
- The field appears **only** on this layout among the credentialing case views; it is **not** referenced in any OmniScript, FlexCard, or FlexiPage.

### Important deployment note (drift)

- OmniStudio source of truth in this repo is the **`vlocity_export/OmniScript/...` DataPacks** (deployed via the vlocity build tool / `export-omnistudio.yaml`).
- The `force-app/main/default/omniScripts/*.os-meta.xml` snapshots have **drifted** from the DataPacks (e.g., `PRM_PSVSubOsWSNPDB_English_8` contains extra editable "Education Level" Select variants not present in the current DataPack export). Reconcile before deploying through `sf project deploy` of the `.os-meta.xml` files.

---

## Acceptance Criteria

**AC-1 — CAQH education type pre-fills Education Level**

**Given** a Credentialing Specialist opens the education step (in Application Review or PSV Education Verification) for a practitioner whose CAQH record returns an education type that matches a valid Education Level option,
**When** the education block loads,
**Then** the Education Level field is pre-filled with the CAQH-provided value,
**And** the specialist can still change it before continuing.

**AC-2 — Education Level defaults to "Professional School" when CAQH has no value**

**Given** a Credentialing Specialist opens the education step (in Application Review or PSV Education Verification) for a practitioner whose CAQH record returns no education type (or the practitioner has no CAQH education record),
**When** the education block loads,
**Then** the Education Level field is pre-filled with "Professional School",
**And** the specialist can change it to any other available education level before continuing.

**AC-3 — The default never overrides a value already present**

**Given** an education record already has an Education Level value (from CAQH or entered earlier in the flow),
**When** the education block loads in either flow,
**Then** the existing value is preserved and displayed,
**And** "Professional School" is applied only when the field would otherwise be empty.

**AC-4 — CAQH education type that has no matching option is handled predictably**

**Given** a Credentialing Specialist opens the education step for a practitioner whose CAQH record returns an education/training type that is not a valid Education Level option (for example, "Fifth Pathway", "Other Training", or "Faculty Positions / Academic Appointments"),
**When** the education block loads,
**Then** the field behaves per the agreed mapping decision (see Clarification Q6) — e.g., it shows the mapped Education Level value, or falls back to "Professional School" — rather than displaying a blank/invalid selection,
**And** the specialist is able to set a valid Education Level before continuing.

**AC-5 — Education Level remains required**

**Given** the Education Level field is pre-filled with the default,
**When** the specialist clears it and tries to continue,
**Then** the flow blocks progression and prompts that Education Level is required (unchanged from today's behavior).

**AC-6 — "CAQH Accessible" no longer appears on the PPR case view**

**Given** a Credentialing Specialist views a Practitioner Participation Request case,
**When** the case page is displayed,
**Then** the "CAQH Accessible" field is no longer shown on the layout,
**And** no other field on the layout is moved or removed.

**AC-7 — "CAQH Accessible" data and automation are unaffected**

**Given** the "CAQH Accessible" field is removed from the PPR case view,
**When** existing CAQH-related automation/batches run,
**Then** the underlying `PRM_CAQHAccessible__c` value continues to be set and read as before,
**And** only the on-screen visibility on the PPR layout changes.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_CredApplicationReviewSubOS_English` → `EducationLevelSF` | OmniScript element (new OS version) | Set `defaultValue` = `"Professional School"` | CAQH block — pre-fills from CAQH when present, else defaults. Drives AC-1, AC-2, AC-3 |
| `PRM_CredApplicationReviewSubOS_English` → `VerifyEducationLevel` | OmniScript element (new OS version) | Add `defaultValue` = `"Professional School"` | Practitioner (manual-entry) block. Drives AC-2 |
| `PRM_PSVSubOsWSNPDB_English` → `EducationLevelSF` | OmniScript element (new OS version) | Set `defaultValue` = `"Professional School"` | CAQH block; keep existing `CaseType <> "QC Review"` show rule. Drives AC-1, AC-2, AC-3 |
| `PRM_PSVSubOsWSNPDB_English` → `VerifyEducationLevel` | OmniScript element (new OS version) | Add `defaultValue` = `"Professional School"` | Practitioner (manual-entry) block. Drives AC-2 |
| `PRMDRTCAQHPersonEducation` / `PRMCAQHReviewTransform` | DataMapper — verify / possible mapping | Confirm `EducationTypeName → EducationLevelSF` direct copy; if business wants CAQH values like "Fifth Pathway" translated, add a value-map step here | Supports AC-4 (pending Clarification Q6) |
| `IndividualApplication – Practitioner Participation Request Layout` | Page layout | Remove the `PRM_CAQHAccessible__c` `layoutItems` entry | Drives AC-6 |
| `PRM_CAQHAccessible__c` field + CAQH automation | No change | Field, FLS, and automation remain intact | Supports AC-7 |

> Implementation guidance: make the OmniScript edits in the **vlocity_export DataPack** element files (or in OmniStudio Designer) and deploy/activate via the vlocity build tool. Avoid hand-editing the compiled `.os-meta.xml` JSON (drifted from DataPacks). OmniStudio `defaultValue` pre-fills **only an empty node**, so the CAQH-sourced value is honored when present and "Professional School" is applied only when the field is empty — this is what satisfies the "pre-fill from CAQH, else default" requirement (AC-1/AC-2/AC-3) with no extra conditional logic. The only open design point is how to treat CAQH education types that aren't valid picklist values (AC-4 / Q6).

---

## Definition of Done

- [ ] All four Education Level elements default to "Professional School" (both blocks in both OmniScripts), new OS versions active.
- [ ] When CAQH returns a valid education type, the field pre-fills with the CAQH value (AC-1 verified in QA).
- [ ] When CAQH returns no education type, the field defaults to "Professional School" (AC-2 verified in QA).
- [ ] Default does not overwrite an existing/CAQH-provided Education Level (AC-3 verified in QA).
- [ ] Behavior for CAQH education types with no matching picklist option (e.g., "Fifth Pathway") agreed (Q6) and verified (AC-4).
- [ ] Education Level still enforced as required (AC-5 verified).
- [ ] `PRM_CAQHAccessible__c` removed from the PPR layout; no other layout items disturbed (AC-6).
- [ ] `PRM_CAQHAccessible__c` value/automation confirmed unchanged after layout edit (AC-7).
- [ ] vlocity DataPack ↔ `.os-meta.xml` drift reconciled (or deploy path confirmed) before promotion.
- [ ] QA verification in sandbox across both flows and the PPR case view.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Confirm the "pre-fill from CAQH, else default to Professional School" logic applies to the **CAQH-sourced** block (`EducationLevelSF`); should the manually-entered practitioner block (`VerifyEducationLevel`) also default to Professional School? (Business approved "all four" in chat — confirm for sign-off.) | Scope of AC-1/AC-2 | BA / Product |
| 2 | Should the default also apply in **QC Review** context (currently those education selects are hidden via `CaseType <> "QC Review"`)? | Whether show-rule needs adjustment | BA / Product |
| 3 | Is removing "CAQH Accessible" intended for the **PPR layout only**, or also Re-credentialing and Individual Application layouts? | Rollout scope of AC-6 | BA / Product |
| 4 | Should the `PRM_CAQHAccessible__c` field itself (and any automation populating it) be deprecated, or only hidden from the PPR view? | Whether AC-7 holds or field is retired | Technical / Product |
| 5 | Confirm deploy path for OmniScripts (vlocity build tool vs. `sf project deploy` of `.os-meta.xml`) given the detected drift. | Deployment correctness | Technical |
| 6 | How should CAQH `EducationTypeName` values that are **not** valid `PersonEducation.EducationLevel` picklist values be handled — currently **"Fifth Pathway", "Other Training", "Faculty Positions / Academic Appointments"**? Per value, choose: (a) add the value to the picklist, (b) map it to an existing picklist value via a DataMapper translation, or (c) fall back to "Professional School". A value-map table is needed. | Drives AC-4; affects DataMapper and/or picklist changes | BA / Product / Technical |
| 7 | Is the full CAQH `EducationTypeName` domain limited to the two value sets captured here (Education Type + Training Type), or can CAQH return other values? A complete CAQH→picklist value map should be confirmed before build. | Completeness of the value map | BA / Product |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_CredApplicationReviewSubOS_English` | OmniScript | MEDIUM | New active version; education step in Initial Cred review |
| `PRM_PSVSubOsWSNPDB_English` | OmniScript | MEDIUM | New active version; PSV education verification step |
| `PRMDRTCAQHPersonEducation` / `PRMCAQHReviewTransform` | DataMapper | LOW–MEDIUM | Only if a CAQH-value→picklist translation is required (Q6); otherwise verify-only |
| `PersonEducation.EducationLevel` picklist | Picklist | LOW | Only if business chooses to add "Fifth Pathway" (Q6) |
| `IndividualApplication – Practitioner Participation Request Layout` | Page layout | LOW | Single read-only field removed |
| `PRM_CAQHAccessible__c` | Custom field / automation | LOW | No change; visibility only |
| `PersonEducation` records | Data quality | LOW (positive) | Fewer blank Education Level values expected |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| 2 OmniScripts × 2 elements | `defaultValue` set + activate new versions | M | AI-estimated — four element edits, two OS activations |
| PPR layout | Remove one layout item | S | AI-estimated — config change |
| Drift reconciliation | DataPack ↔ `.os-meta.xml` review | S–M | AI-estimated — depends on chosen deploy path |
| QA | Manual verification (both flows + PPR view) | M | AI-estimated |

**Total Estimated Effort:** ~M (metadata/config change, no new Apex) — **AI-estimated, validate with team**
