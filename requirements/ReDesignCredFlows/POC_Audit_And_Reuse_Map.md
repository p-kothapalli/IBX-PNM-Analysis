# Credentialing LWC Redesign — POC Audit & Reuse Map

> **Purpose:** A thorough audit of the `requirements/ReDesignCredFlows/` plan against what is **already built and running in the org**, plus a concrete reuse map for a demo POC. Companion docs: `POC_Execution_Plan.md` (how we build it) and `POC_Claude_Code_Prompt.md` (the prod-ready build prompt).
>
> **Reading guide (mirrors `docs/implementation-plan` convention):** items are tagged **[CONFIRMED]** (verified against repo source), **[GAP]** (plan omits / contradicts reality), **[RISK]**, **[OPEN]** (needs a decision), **[RECOMMENDATION]**.
>
> **Date:** 2026-06-23 · **Status:** DRAFT for review

---

## 1. What the plan says (summary of `MASTER_Development_Plan_…`)

- **[CONFIRMED]** Goal: replace 6 OmniScript credentialing flows (Application Review, Initial/Re-Cred PSV, Initial/Re-Cred PSV QC, PDA QC) with a **tile-based LWC dashboard** that saves each tile independently (kills the 4 MB "Save for Later" limit), supports pause/resume, shows visual progress, and lets reviewers edit Salesforce fields inline while CAQH stays read-only.
- **[CONFIRMED]** Proposed scope: **49 LWC components + 7 Apex controllers + 2 custom objects** over ~13 weeks (parallel) / ~24.5 weeks (sequential).
- **[CONFIRMED]** Proposed framework: 6 shared framework LWCs (`prm_verificationDashboard`, `prm_progressHeader`, `prm_verificationTile`, `prm_verificationModal`, `prm_navigationFooter`, `prm_qcWrapper`), 4 shared sub-components, 2 custom objects (`PRM_VerificationSession__c`, `PRM_VerificationTileStatus__c`).
- **[CONFIRMED]** Persistence design: tile state in custom objects (Draft JSON), aggregate to the legacy IP (`PRM_ReviewPSVCaseRecordsUpdate`) on final submit.

---

## 2. The central finding

> **[GAP] The plan is written as a greenfield build of 49 components, but the org already contains a mature, production-grade "Action Center" component ecosystem that implements the exact inline-edit + modal + notes + datatable + CAQH-read-only patterns the plan re-specifies from scratch.** None of the 7 redesign design docs reference a single existing component or Apex controller (verified: grep for `prmLaunch*`, `prmNotesCapture`, `prmPractitionerSummary`, `prmAppReviewCaqhMatch`, and the existing controllers across `requirements/ReDesignCredFlows/` returns **zero matches**).

The four URLs you supplied are these already-deployed components:

| Your link | Component (deployed) | What it already does |
|---|---|---|
| Credentials Management | `prmLaunchCredentialsAction` | BusinessLicense datatable + row Edit/Remove + inline create modal, picklist wires, duplicate detection, date-range validation, notes capture, humanized save errors |
| Contact Information | `prmLaunchContactAction` | Primary/secondary contact edit, contact-picker search modal, phone formatter, dirty-gated save, duplicate-contact guard, notes |
| Provider Action Center | `prmLaunchProviderAction` | 5 tabs (Provider Identity/diversity, Languages, Pronouns, Affirming Care, embedded Practitioner Info), multi-select pickers w/ caps, per-tab dirty + save, notes |
| Address Action Center | `prmLaunchAddressAction` | Active/Pending/Billing-Mailing locations + multi-step **Add New Location** wizard (Group → Address → Precisely standardization → Review → Save), taxonomy/telehealth logic, NPI validation |

These are **not stubs** — they are full, defensive, console-aware LWCs (e.g. `prmLaunchProviderAction.js` is ~2,380 lines) backed by real Apex controllers with test classes.

---

## 3. Existing reusable inventory (verified in `force-app/main/default`)

### 3.1 The four "edit functionality" action centers
- **[CONFIRMED]** `prmLaunchCredentialsAction`, `prmLaunchContactAction`, `prmLaunchProviderAction`, `prmLaunchAddressAction` — all `isExposed=true`, target `lightning__UrlAddressable`, take `recordId` from `c__recordId` page state (the IndividualApplication / Case Manager Id), launched as console subtabs.
- **[CONFIRMED]** A fifth sibling exists: `prmLaunchPractitionerAction` (embedded inside the Provider action center).

### 3.2 Shared building blocks (the de-facto framework that already exists)
| Component | Role | Maps to plan's… |
|---|---|---|
| `prmGenericButtonLauncher` | Renders the action buttons; opens/focuses console subtabs via `platformWorkspaceApi`; passes `recordId` | partial `prm_verificationDashboard` (launch/orchestration) |
| `prmPractitionerSummary` | Read-only practitioner snapshot card (`@api refresh()`), `cacheable` wire | `prm_practitionerDemographics` (read-only half) |
| `prmNotesCapture` | Reusable notes textarea: `getNoteText/reportValidity/reset`, required + maxlength | reason/notes pattern in every tile |
| `prmGenericInlineError` | Inline error banner | error badge/banner |
| `prmGenericConfirmModal` | Generic confirm dialog | confirmation dialogs |
| `prmGenericPagination` | Pagination | address/network pagination (Risk #2) |
| `prmGenericSearchInput` | Search box | tile search/filter |
| `prmEnhancedDatatable` | Datatable wrapper | every tile datatable |
| `prmMultiSelect` / `prmMultiSelectPicklist` / `prmCheckboxList` | Multi-select pickers | taxonomy/network/language pickers |
| `prmAppReviewCaqhMatch` (+ `PRM_AppReviewMatchController`, `PRM_CAQHMatchScoreService`) | CAQH match/compare UI + scoring | the CAQH read-only vs SF-editable side-by-side |
| `prmAddressComparison`, `prmAddressDetailsForm`, `prmSmartAddressSearch`, `prmActiveLocations`, `prmPendingLocations`, `prmBillingMailingLocations`, `prmGroupInfoEntry` | Address sub-flow | the "LARGEST TILE" (Address Verification) |
| `prmContentDocumentViewer`, `prmViewFileFromSDS`, `prmLetterDocuments` | File view/preview | `prm_fileUpload` (view side) |

### 3.3 Apex controllers/services already serving the above (verified)
- **[CONFIRMED]** `PRM_BusinessLicenseController` (get/create/update/errorOut), `PRM_ContactInformationController` (get/search/save), `PRM_ProviderInformationController` (languages/pronouns/affirming-care/identity get+save + picklist options), `PRM_AddNewLocationUtility` + `PRM_PreciselyAddressService` + `PRM_GroupNpiValidationService`, `PRM_ActiveLocationsController.getPractitionerSummary`.
- **[CONFIRMED]** CAQH layer: `PRM_AppReviewMatchController`, `PRM_CAQHMatchScoreService`, `PRM_CAQHValidationService`, `PRM_CaqhAuthController` (+ tests for all).
- **[CONFIRMED]** Selectors exist (e.g. `PRM_AddressSelector`) — reuse, don't rebuild (consistent with the high-volume program's CL-8).

### 3.4 What genuinely does NOT exist yet
- **[CONFIRMED]** `PRM_VerificationSession__c` and `PRM_VerificationTileStatus__c` objects — **not present** in `force-app/main/default/objects` (grep returns none).
- **[CONFIRMED]** A tile-grid dashboard shell, progress header, tile card, and generic modal wrapper as *standalone reusable* components — not present (the launcher is button-list, not a tile grid; modals today live inside each action center).
- **[CONFIRMED]** Session pause/resume persistence and cross-tile progress tracking — not present.
- **[CONFIRMED]** `prm_qcWrapper` (read-only PSV + editable QC) — not present.

---

## 4. Audit: plan vs. reality (issues to resolve)

| # | Finding | Severity | Recommendation |
|---|---|---|---|
| A1 | Plan rebuilds editing tiles (Contact, Provider/diversity/languages, License, Address) that already exist as polished action centers | **High** (≈40–60% wasted effort) | **Reuse the action centers**; build only the missing shell + objects. |
| A2 | Plan ignores existing Apex controllers; proposes new `ApplicationReviewController`, `PSVReviewController`, etc. | High | Reuse `PRM_BusinessLicenseController` / `PRM_ContactInformationController` / `PRM_ProviderInformationController` / `PRM_AddNewLocationUtility`; add only a thin **session/tile-status controller**. |
| A3 | Plan re-specs CAQH side-by-side from scratch; `prmAppReviewCaqhMatch` + match-scoring services already exist | Medium | Reuse the CAQH match component/services for the read-only compare panel. |
| A4 | Action centers are `UrlAddressable` console subtabs, not embeddable tiles; they read `c__recordId` from page state, not always `@api recordId` | Medium **[RISK]** | For in-dashboard embedding, set `@api recordId` directly (the JS already falls back to it). Minimal change: add `lightning__RecordPage`/`lightning__AppPage` targets or a thin wrapper. |
| A5 | Plan's "auto-save" was removed (v1.1) but tiles still imply draft JSON; action centers **save straight to Salesforce on submit** (no draft) | Medium | POC persistence = **tile completion status** only (not field drafts); the action centers already persist their own data immediately. This actually *simplifies* the session object. |
| A6 | Each action center owns its own modal/tabs; plan assumes one generic `prm_verificationModal` injecting children via `lwc:component` | Medium | For POC, **launch action centers as subtabs from tiles** (reuse `prmGenericButtonLauncher`'s proven subtab logic) instead of dynamic injection. Dynamic `lwc:component` injection is the riskier path; defer. |
| A7 | Timeline assumes 49 net-new components; reuse collapses Flow 1/2 editing scope dramatically | Low (positive) | Re-baseline estimates after POC (see Execution Plan §8). |
| A8 | QC flows (4,5) and PDA QC (6) have the least existing reuse (`prm_qcWrapper`, networks dual-listbox, directory cascade are net-new) | Medium | Keep QC/PDA out of the POC; POC proves reuse on App Review + PSV editing surface. |

---

## 5. Reuse map for the demo POC

**POC objective:** prove the redesign vision (tile dashboard + progress + pause/resume + inline edit + CAQH read-only) by **reusing the 4 action centers as tiles**, building only the missing shell and the 2 objects.

| Layer | Build new? | Asset |
|---|---|---|
| Tile dashboard shell | **NEW (thin)** | `prmVerificationDashboard` — tile grid, reads tile statuses, launches action centers |
| Progress header | **NEW (thin)** | `prmProgressHeader` — X/Y complete, last-saved, reviewer (or reuse a card) |
| Tile card | **NEW (thin)** | `prmVerificationTile` — status badge + click |
| Tile launch/orchestration | **REUSE** | `prmGenericButtonLauncher` subtab open/focus logic (lift into dashboard) |
| Practitioner snapshot | **REUSE** | `prmPractitionerSummary` |
| Credentials/License editing | **REUSE** | `prmLaunchCredentialsAction` + `PRM_BusinessLicenseController` |
| Contact editing | **REUSE** | `prmLaunchContactAction` + `PRM_ContactInformationController` |
| Provider/diversity/languages editing | **REUSE** | `prmLaunchProviderAction` + `PRM_ProviderInformationController` |
| Address / Add-Location | **REUSE** | `prmLaunchAddressAction` + `PRM_AddNewLocationUtility` + `PRM_PreciselyAddressService` |
| CAQH read-only compare | **REUSE** | `prmAppReviewCaqhMatch` + `PRM_AppReviewMatchController` |
| Notes / inline error / confirm / datatable / pagination | **REUSE** | `prmNotesCapture`, `prmGenericInlineError`, `prmGenericConfirmModal`, `prmEnhancedDatatable`, `prmGenericPagination` |
| Session + tile status persistence | **NEW** | `PRM_VerificationSession__c`, `PRM_VerificationTileStatus__c` + `PRM_VerificationSessionController` |

**Estimated reuse for the POC editing surface: ~75–85%.** New code is limited to: 2 objects, 1 controller, 3 thin shell LWCs, and small `@api recordId` exposure tweaks on the action centers.

---

## 6. Open questions (decide before/at POC kickoff)

- **[OPEN] OQ-1 — Target org:** POC org alias (the links point to `ibx--qa`; confirm we build/deploy there or a scratch org).
- **[OPEN] OQ-2 — Embed vs. subtab:** Should tiles **launch action centers as console subtabs** (lowest risk, reuses proven code) or **open them inside a modal** (closer to mockup, needs `@api recordId` + modal host)? *Recommendation: subtab for POC, modal as a fast-follow.*
- **[OPEN] OQ-3 — Persistence depth:** POC persists **tile completion status only** (recommended) vs. also field drafts. Action centers already commit data on save, so drafts are redundant.
- **[OPEN] OQ-4 — Which flow for the POC:** Recommend **Application Review** (baseline) using the 4 action centers as the editable tiles + CAQH compare; QC/PDA explicitly out.
- **[OPEN] OQ-5 — Tile↔component mapping sign-off:** confirm the App Review tile list maps onto the 4 action centers (some App Review tiles — Education, Work History, Malpractice, Adverse Action — have no existing editor and would be read-only/stub for the POC).

---

## 7. Risks specific to reuse

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Action centers depend on console (`platformWorkspaceApi`) for cancel/close | Med | Med | JS already no-ops outside console; dashboard provides its own close path |
| R2 | `recordId` arrives via `c__recordId` page state, not `@api` when embedded | High | Low | Set `@api recordId` on embed; wires already react to it |
| R3 | Action centers commit immediately (no dashboard-level transaction) | Med | Med | POC treats each tile as independently saved (matches plan intent) |
| R4 | `apiVersion` drift across bundles (64/65) | Low | Low | Normalize on deploy |
| R5 | Some App Review tiles have no existing editor (Education/Work History/Malpractice/Adverse Action) | Med | Med | Mark read-only/stub in POC; flag for phase 2 |
