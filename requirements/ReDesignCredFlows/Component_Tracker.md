# Credentialing LWC Redesign — Component Tracker

> **Purpose:** Single source of truth for every component in the Credentialing tile-redesign effort — what is **new** vs **reused-by-reference**, build/test/deploy status, target org, and brand-style-guide compliance. Update this file whenever a component is created, deployed, or changed.
>
> **Maintained by:** Cursor AI Agent · **Last updated:** 2026-06-27

> **🔄 Combined flow (2026-06-27):** Application Review + Initial Cred PSV are now **one "Initial Credentialing Review" flow** (17 tiles) per the master plan v2.0. This **resolves the earlier "flow mismatch" audit note** — the POC board legitimately includes both App-Review-origin tiles (Education, License, Work History, Malpractice…) **and** PSV-origin action centers (Contact, Provider/Diversity, Address, CAQH) because they belong to the same combined flow. The previously "unwired" PSV action centers (`prmLaunchContactAction`, `prmLaunchAddressAction`, `prmAppReviewCaqhMatch`, `prmLaunchProviderAction`) can be **re-added to the board** as part of the combined tile set.

---

## Legend
- **Status:** `Built` · `Deployed` · `Planned` · `Reused (no change)`
- **Origin:** `NEW` (created by us) · `REUSE` (existing org artifact, referenced only — never edited)
- **Brand:** ✅ IBX brand tokens applied · ➖ N/A (not ours) · ⚠️ needs alignment

---

## 1. POC — UI Components (Phase: UI-only demo)

**Target org:** `qa-sandbox` (`prashanth.kothapalli@ibx.com.pie.qa`, Org Id `00DVB000009WnBh2AK`)
**Deploy ID:** `0AfVB00000HYY3u0AH` · **Deployed:** 2026-06-23

| Component | Type | Origin | Status | Tests | Coverage | Brand | Notes |
|---|---|---|---|---|---|---|---|
| `prmCredTileCard` | LWC (presentational) | NEW | **Deployed** | 19 Jest ✅ | 90.5% | ✅ | Tile card: icon + label + **required indicator** + **status icon + badge** + **CAQH-style warning row** + **Modified/By footer** + Coming-Soon ribbon; ARIA + keyboard; emits `tileselect`. Upgraded 2026-06-24 to match the design's `prm_verificationTile` spec. |
| `prmCredTileProgress` | LWC (presentational) | NEW | **Deployed** | 6 Jest ✅ | 100% | ✅ | SLDS progress bar + "X of Y completed"; brand-accent fill. |
| `prmCredTileBoard` | LWC (container) | NEW | **Deployed** | 10 Jest ✅ | 92.4% | ✅ | Embeds summary, holds tile config, routes launches (subtab/nav). `lightning__RecordPage` (IndividualApplication) + `lightning__AppPage`. **Self-guard:** renders only for `USER_ID === 005UW00000EJHZqYAP` (QA demo user). **Realigned 2026-06-24** to the **Application Review 10-tile inventory** (Review Application, Verify Taxonomy, Verify Education, Verify License (SBRD), Verify Work History, Verify DEA, Verify CDS, Verify Malpractice, Upload Attachments, Final Submit) per `Application_Review_LWC_Redesign_Detailed_Design.md`. Only **Review Application** (→ `prmLaunchProviderAction`) and **Verify License** (→ `prmLaunchCredentialsAction`) have existing editors; the rest are "Coming Soon". |
| ~~`PRM_CredTileDemo_CaseManager`~~ | FlexiPage | NEW | **Deleted** | — | — | ➖ | Removed 2026-06-24 — not needed. `prmCredTileBoard` is placed directly on the existing `PRM_CaseManagerRecordPage` via App Builder; the board's own user self-guard handles single-user visibility. |

**Aggregate:** 35 Jest tests passing · 92.62% line coverage · ESLint clean · Prettier formatted. Board + card redeployed to `qa-sandbox` on 2026-06-24 (App Review realignment) — Deploy ID `0AfVB00000HZAQv0AP`.

> **⚠️ Audit note (2026-06-24) — ✅ RESOLVED 2026-06-27 by the combined flow:** The original board tiles were chosen by "which existing action center can we reuse," which surfaced PSV tiles (Contact, Provider/Diversity, Address, CAQH) under an "Application Review" label — flagged then as a flow mismatch. **With App Review + PSV now merged into one Initial Credentialing Review flow, this is no longer a mismatch** — those PSV action centers and the App-Review-origin tiles are all part of the same 17-tile combined flow. **Recommended next board iteration:** present the **combined 17-tile inventory** (re-wire the PSV action centers that were removed on 2026-06-24) rather than the App-Review-only 10-tile set.

---

## 1A. POC — CAQH Profile Viewer (Phase: UI-only demo)

**Target org:** `qa-sandbox` (`prashanth.kothapalli@ibx.com.pie.qa`) · **Deploy ID:** `0AfVB00000Hbrd40AB` · **Deployed:** 2026-06-26

| Component | Type | Origin | Status | Tests | Brand | Notes |
|---|---|---|---|---|---|---|
| `prmCaqhProfile` | LWC (presentational) | NEW | **Deployed** | 8 Jest ✅ | ✅ | Read-only panel on the Case Manager (`IndividualApplication`) record page. **"Fetch CAQH Data" button** pulls the full CAQH provider profile and renders it as curated, collapsible `lightning-accordion` sections. **Coverage expanded 2026-06-26** to ~20 sections: Identity & Demographics, Indicators (flags), Other Name, Licenses, DEA, CDS, Medicare/Medicaid, Specialty & Board, Education, Work History, Time Gaps, Malpractice, Hospital Affiliations, Practice Locations, Languages Spoken, Certifications, Disclosures, References, Provider Address, Credentialing Contact. **UI redesign 2026-06-26:** full-width stacked record cards with a responsive **label-above-value field grid** (no more ragged right-aligned wrapping); long free-text fields (disclosure explanations, practice "Accepting Patients"/Services/Accessibility/Languages, addresses) span the full row via a `wide` flag; title-duplicating fields removed; IBX brand tokens + Arial; prompt spacing fixed. **Self-guard:** renders only for `USER_ID === 005UW00000EJHZqYAP`. New files only — no existing component edited. |
| `PRM_CaqhProfileController` | Apex | NEW | **Deployed** | 6 Apex ✅ | ➖ | Resolves the CAQH provider id from `IndividualApplication → Account → Identifier` (`PRM_Type__c='CAQH'`, `PRM_AttestationID__c`) and **reuses by reference** the existing live callout `PRM_AppReviewCaseAssembler.fetchCaqh(...)` (Integration Procedure `PRM_ValidateCAQHAppReviewParent`). Shapes the nested `Provider` payload (normalizes single-Map vs List nodes) into a curated read-only view model. `with sharing`, `WITH USER_MODE`, `cacheable=false` (callout). **Inactive-tolerant (2026-06-26):** does **not** require `PRM_Active__c=true` (right after PAR submit the Identifier is still inactive) — prefers active, falls back to most-recent; renders the profile whenever CAQH returns a `Provider` node even if it flags `InactiveCAQH`/`APIError` (surfacing a note). |
| `PRM_CaqhProfileControllerTest` | Apex (test) | NEW | **Deployed** | — | ➖ | Bypasses the live callout via the existing `@TestVisible PRM_AppReviewCaseAssembler.caqhOverride`; covers curation (single + repeating sections), no-identifier, inactive-CAQH, blank-id, and invalid-id paths. 100% of test methods pass. |

**Aggregate:** 8 Jest + 5 Apex tests passing · ESLint clean. Built off a live CAQH discovery call (active provider `16174855`) that enumerated the full CAQH response schema.

> **Reused by reference (CAQH viewer):** `PRM_AppReviewCaseAssembler.fetchCaqh()` (live IP callout) and IP `PRM_ValidateCAQHAppReviewParent` / named credential `PRM_CAQH_API` — **not modified**.

---

## 2. Reused by reference (existing org artifacts — NOT modified)

| Component | Type | How reused | Touched? |
|---|---|---|---|
| `prmLaunchCredentialsAction` | LWC (UrlAddressable) | Launched as subtab from **Verify License (SBRD)** tile | ❌ No |
| `prmLaunchProviderAction` | LWC (UrlAddressable) | Launched as subtab from **Review Application** tile (hosts Practitioner Info) | ❌ No |
| `prmPractitionerSummary` | LWC | Embedded read-only child `<c-prm-practitioner-summary>` | ❌ No |
| `prmGenericButtonLauncher` | LWC | Subtab launch logic **copied** into `prmCredTileBoard` | ❌ No (copy only) |
| `prmLaunchContactAction` · `prmLaunchAddressAction` · `prmAppReviewCaqhMatch` | LWC (UrlAddressable) | Removed from the board on 2026-06-24; **with the combined flow (2026-06-27) these are back in scope** — re-wire them as combined-flow tiles (Contact, Address, CAQH Compare). | ❌ No |

---

## 3. Planned / not yet built (future phases — out of POC scope)

| Component | Type | Origin | Status | Notes |
|---|---|---|---|---|
| `PRM_VerificationSession__c` | Custom Object | NEW | Planned | Pause/resume + tile-status persistence (full build, not UI demo). |
| `PRM_VerificationTileStatus__c` | Custom Object | NEW | Planned | Per-tile completion state. |
| `PRM_VerificationSessionController` | Apex | NEW | Planned | Thin session/tile-status controller. |
| Education / Work History / Malpractice / File Upload / Final Submit tiles | Editors | NEW | Planned | Currently "Coming Soon" placeholders in the board. |
| `prm_qcWrapper` (QC / PDA flows) | LWC | NEW | Planned | Least existing reuse; explicitly out of POC. |

---

## 4. Deploy history

| Date | Org | Deploy ID | Components | Result |
|---|---|---|---|---|
| 2026-06-23 | `qa-sandbox` (ibx PIE/QA) | `0AfVB00000HYY3u0AH` | 3 LWC + 1 FlexiPage | ✅ Success |
| 2026-06-23 | `qa-sandbox` (ibx PIE/QA) | `0AfVB00000HYadZ0AT` | FlexiPage (added single-user visibility rule) | ✅ Success |
| 2026-06-23 | `qa-sandbox` (ibx PIE/QA) | `prmCredTileBoard` redeploy | Board self-guard: render only for QA demo user | ✅ Success |
| 2026-06-24 | `qa-sandbox` (ibx PIE/QA) | `0AfVB00000HZ8gr0AD` | **Deleted** FlexiPage `PRM_CredTileDemo_CaseManager` (using existing page instead) | ✅ Success |
| 2026-06-24 | `qa-sandbox` (ibx PIE/QA) | `0AfVB00000HZAQv0AP` | `prmCredTileBoard` + `prmCredTileCard` — App Review 10-tile realignment + upgraded tile card | ✅ Success |
| 2026-06-26 | `qa-sandbox` (ibx PIE/QA) | `0AfVB00000Hbrd40AB` | `prmCaqhProfile` LWC + `PRM_CaqhProfileController` + test — CAQH Profile viewer (5 Apex tests ✅) | ✅ Success |
| 2026-06-26 | `qa-sandbox` (ibx PIE/QA) | `0AfVB00000HbttO0AR` | `PRM_CaqhProfileController` + test — pull CAQH data even when the Identifier is inactive (6 Apex tests ✅) | ✅ Success |
| 2026-06-26 | `qa-sandbox` (ibx PIE/QA) | `0AfVB00000HbxVZ0AZ` | `PRM_CaqhProfileController` + test — resolve CAQH id from `IdValue` when `PRM_AttestationID__c` is null (post-PAR-submit). Verified live on `0iTVB000000HncD2AS` → 10 sections (7 Apex tests ✅) | ✅ Success |
| 2026-06-26 | `qa-sandbox` (ibx PIE/QA) | `prmCaqhProfile` + controller redeploy | **Section coverage expansion** (full CAQH schema → ~20 sections, incl. CDS, Medicare/Medicaid, Languages, References, Time Gaps, Other Name, Indicators) + **UI redesign** (stacked full-width cards, label-above-value grid, wide long-text fields, prompt spacing fix) + graceful handling of inactive/error CAQH ids. Validated against 31 test ids (16 returned providers). (7 Apex + 8 Jest ✅) | ✅ Success |

---

## 5. Outstanding actions

- [x] ~~Activate `PRM_CredTileDemo_CaseManager`~~ — page deleted; `prmCredTileBoard` placed directly on `PRM_CaseManagerRecordPage` via App Builder.
- [x] ~~Realign board to the Application Review 10-tile inventory~~ — done 2026-06-24 (board config + upgraded tile card). Jest 35 ✅ / 92.62%.
- [x] ~~Redeploy `prmCredTileBoard` + `prmCredTileCard` to `qa-sandbox`~~ — done 2026-06-24, Deploy ID `0AfVB00000HZAQv0AP`.
- [ ] Smoke test on a real Case Manager record in a console app (verify Review Application + Verify License subtab launches + Coming-Soon toasts for the other tiles).
- [x] ~~Decide whether a flow-aware tile set (App Review vs PSV) is wanted~~ — **superseded 2026-06-27:** App Review + PSV are now ONE combined flow. **Next:** rebuild the board to the **combined 17-tile inventory** (re-wire Contact/Address/CAQH/Provider action centers).
- [ ] Decide status mode evolution (static → client-side → derived) for the next iteration.
- [ ] Add `prmCaqhProfile` to the Case Manager record page via App Builder (drag onto `PRM_CaseManagerRecordPage`), then smoke test "Fetch CAQH Data" on a practitioner with an **active** CAQH id (most QA records are inactive; verified active id `16174855`).
- [ ] Decide whether the CAQH viewer should also offer a "View raw JSON" toggle (curated-only chosen for the demo).
