# Credentialing Tile UI — POC Build Notes (UI Components Only)

> **Built to:** `POC_UI_Components_Execution_Plan.md` + `POC_UI_Components_Claude_Prompt.md`
> **Date:** 2026-06-23
> **Scope:** UI-only tile dashboard for the Case Manager (`IndividualApplication`) record page. **No backend, no new Apex, no new objects, and zero edits to any existing artifact.** Every change is a new file.

---

## 1. What was created (new files only)

### New LWC bundles (3)
| Bundle | Role | Exposed | Targets |
|---|---|---|---|
| `force-app/main/default/lwc/prmCredTileCard` | Presentational tile card (icon + label + status badge + Coming-Soon ribbon) | `false` | — (child only) |
| `force-app/main/default/lwc/prmCredTileProgress` | Presentational progress header (SLDS bar + "X of Y completed" + reviewer/last-saved) | `false` | — (child only) |
| `force-app/main/default/lwc/prmCredTileBoard` | Container: practitioner summary + progress + responsive tile grid + launch routing | `true` | `lightning__RecordPage` (IndividualApplication), `lightning__AppPage` |

Each bundle includes `.js`, `.html`, `.css`, `.js-meta.xml` (apiVersion **64.0**, matching the action centers) and a `__tests__/*.test.js`.

### New FlexiPage (1)
- `force-app/main/default/flexipages/PRM_CredTileDemo_CaseManager.flexipage-meta.xml` — a **new, dedicated** record page for `IndividualApplication` hosting `c:prmCredTileBoard` (per plan OQ-UI-3 recommendation: a separate demo page avoids touching the existing `PRM_CaseManagerRecordPage`).

### This document
- `requirements/ReDesignCredFlows/POC_UI_Build_Notes.md`

---

## 2. What was reused (BY REFERENCE ONLY — never modified)

| Reuse | How | Existing artifact (untouched) |
|---|---|---|
| Credentials / License editor | Launched as console subtab / nav | `c__prmLaunchCredentialsAction` |
| Contact Information editor | Launched as console subtab / nav | `c__prmLaunchContactAction` |
| Provider & Diversity editor | Launched as console subtab / nav | `c__prmLaunchProviderAction` |
| Address / Locations editor | Launched as console subtab / nav | `c__prmLaunchAddressAction` |
| CAQH Compare | Launched as console subtab / nav | `c__prmAppReviewCaqhMatch` |
| Practitioner snapshot | Embedded read-only child tag `<c-prm-practitioner-summary>` | `prmPractitionerSummary` |
| Subtab launch logic | **Copied** `openOrFocusSubtab` / `findExistingSubtab` / `buildPageReference` / `matchesSubtab` + `platformWorkspaceApi` imports into the new board | `prmGenericButtonLauncher` (copied from, not edited) |

All targets verified present in `force-app/main/default/lwc`. The launch components are `isExposed=true`, `lightning__UrlAddressable`, and read `c__recordId` from page state — the board passes `state: { c__recordId: recordId }`, so they are scoped to the same Case Manager with no change required on their side.

---

## 3. Decisions on the plan's Open Questions

| OQ | Decision taken in this build | Notes |
|---|---|---|
| **OQ-UI-1 — Target org** | **Deployed to QA** — `qa-sandbox` (`prashanth.kothapalli@ibx.com.pie.qa`), Deploy ID `0AfVB00000HYY3u0AH`, 2026-06-23. | Validate-only first, then deploy; both clean. |
| **OQ-UI-2 — Status mode** | **(a) Static demo statuses** from the config constant (plan recommendation). | Config shaped so client-side (b) / derived (c) status can layer on later without rework. |
| **OQ-UI-3 — Placement** | **New dedicated FlexiPage** `PRM_CredTileDemo_CaseManager` (recommended; no existing page edited). | Alternative: drag `prmCredTileBoard` onto the existing record page via App Builder (manual, no metadata edit). |
| **OQ-UI-4 — Embed model** | **Subtab launch** (modal would require editing the action centers — forbidden). | Off-console fallback uses `NavigationMixin.Navigate`. |

---

## 4. Tile configuration (static demo — Application Review)

Constant in `prmCredTileBoard.js`. Progress counts derive from these statuses (completed = 2, total = 10).

| tileId | label | icon | status | available | target |
|---|---|---|---|---|---|
| credentials | Credentials / License | utility:identity | Completed | ✅ | `c__prmLaunchCredentialsAction` |
| contact | Contact Information | utility:contact_request | Completed | ✅ | `c__prmLaunchContactAction` |
| provider | Provider & Diversity Info | utility:user | In Progress | ✅ | `c__prmLaunchProviderAction` |
| address | Address / Locations | utility:location | Pending | ✅ | `c__prmLaunchAddressAction` |
| caqh | CAQH Compare | utility:comparison | Pending | ✅ | `c__prmAppReviewCaqhMatch` |
| education | Education | utility:education | Pending | ⛔ Coming Soon | — |
| workHistory | Work History | utility:work_order_type | Pending | ⛔ Coming Soon | — |
| malpractice | Malpractice | utility:shield | Pending | ⛔ Coming Soon | — |
| files | File Upload | utility:upload | Pending | ⛔ Coming Soon | — |
| finalSubmit | Final Submit | utility:check | Pending | ⛔ Coming Soon | — |

---

## 5. Deploy steps (DONE — deployed to `qa-sandbox` 2026-06-23, Deploy ID `0AfVB00000HYY3u0AH`)

```bash
# Validate-only first (replace alias as needed)
sf project deploy start \
  -d force-app/main/default/lwc/prmCredTileCard \
  -d force-app/main/default/lwc/prmCredTileProgress \
  -d force-app/main/default/lwc/prmCredTileBoard \
  -d force-app/main/default/flexipages/PRM_CredTileDemo_CaseManager.flexipage-meta.xml \
  --dry-run -o <ORG_ALIAS>

# Deploy
sf project deploy start \
  -d force-app/main/default/lwc/prmCredTileCard \
  -d force-app/main/default/lwc/prmCredTileProgress \
  -d force-app/main/default/lwc/prmCredTileBoard \
  -d force-app/main/default/flexipages/PRM_CredTileDemo_CaseManager.flexipage-meta.xml \
  -o <ORG_ALIAS>
```

After deploy: in **App Builder → Activation**, assign `Cred Tile Demo - Case Manager` to the demo app/profile (org-default or app-specific) so it renders for the demo user. (Activation is an org-side step; no existing FlexiPage is modified.)

---

## 6. Demo script

1. Open any **Case Manager (`IndividualApplication`)** record in a **console app**.
2. The board renders: practitioner header (read-only `prmPractitionerSummary`) → progress bar ("2 of 10 completed") → a responsive grid of 10 tiles with status badges.
3. Click **Credentials / License** → the existing Credentials action center opens as a focused **subtab** scoped to the same record. Repeat for Contact, Provider, Address, CAQH Compare — each opens its existing editor, **with zero edits**.
4. Re-click an already-open tile → it **focuses the existing subtab** instead of duplicating it.
5. Click **Education / Work History / Malpractice / File Upload / Final Submit** → a **"Coming Soon"** info toast (muted tile + ribbon), not an error.
6. Keyboard: Tab to a tile, press **Enter/Space** → same launch behavior (accessible).
7. Off-console (e.g. app page) → tiles navigate via `standard__component` page reference instead of a subtab.

---

## 7. Tests & quality

- **Jest:** 26 tests across the 3 bundles — all pass.
  - `prmCredTileCard` (12): badge per status, Coming-Soon ribbon/muted, ARIA (role/tabindex/aria-label), `tileselect` on click + Enter + Space, non-activation key ignored.
  - `prmCredTileProgress` (6): summary text, percent + bar width, zero-state safety, aria-valuenow, reviewer/last-saved meta.
  - `prmCredTileBoard` (9): grid renders 10 tiles + progress + summary, recordId passed to summary, off-console navigation target/recordId, console subtab open + label, focus-existing-subtab dedup, Coming-Soon toast, `c__recordId` page-state fallback, no-record-context warning.
- **Coverage** (new bundles): **94.79% lines / 100% funcs** overall — above the ≥85% gate.

```
-------------------------|---------|----------|---------|---------|
File                     | % Stmts | % Branch | % Funcs | % Lines |
-------------------------|---------|----------|---------|---------|
All files                |   95.37 |    83.33 |     100 |   94.79 |
 prmCredTileBoard.js     |   94.02 |       75 |     100 |   93.44 |
 prmCredTileCard.js      |   95.83 |    86.66 |     100 |   95.23 |
 prmCredTileProgress.js  |     100 |      100 |     100 |     100 |
-------------------------|---------|----------|---------|---------|
```

- **Prettier:** all new files formatted. **ESLint:** clean (0 problems) on the new JS.
- **IBX brand style guide:** CSS uses IBX semantic brand tokens (accessible blue `#007DB6`, teal accent `#00AEC7`, brand green/red for status, neutral ink) instead of SLDS-default hexes, with a `data-brand="amerihealth"` theme flip — per `requirements/Mockup_Brand_Style_Guide.md`. Typography/chrome stays on SLDS (correct for internal admin tools per guide §4).

---

## 8. Proof of "no edits to existing components"

`git status --porcelain` for the POC paths shows **only new (`??`) files**:

```
?? flexipages/PRM_CredTileDemo_CaseManager.flexipage-meta.xml
?? lwc/prmCredTileBoard/
?? lwc/prmCredTileCard/
?? lwc/prmCredTileProgress/
```

`git diff --stat` (tracked changes) lists **only pre-existing, unrelated environment files** that this build did **not** touch:

```
 .cursor/skills/README.md        | 35 +++++-   (pre-existing, not part of this work)
 .vscode/settings.json           |  3 +-      (editor/org config, not part of this work)
 config/project-scratch-def.json |  2 +-      (org name, not part of this work)
```

None of the reused action centers, controllers, `prmPractitionerSummary`, `prmGenericButtonLauncher`, objects, fields, permission sets, or the existing `PRM_CaseManagerRecordPage` were modified. ✅

---

## 9. Acceptance gates — status

| Gate | Status |
|---|---|
| AC1 Board renders header + progress + tile grid on Case Manager page | ✅ (verify on deploy) |
| AC2 Correct status styling; AC4 Coming-Soon for placeholders | ✅ |
| AC3 Reuse tile opens mapped action center scoped to recordId, zero edits | ✅ (subtab/nav launch) |
| AC5 Responsive SLDS grid + keyboard-accessible tiles | ✅ |
| AC6 ≥85% Jest coverage; clean deploy; git diff only new files | ✅ tests/coverage/diff; deployed to QA |

---

## 10. Out of scope (not built, by design)

No persistence, no `PRM_VerificationSession__c` / `PRM_VerificationTileStatus__c`, no new Apex, no pause/resume, no final-submit aggregation, no QC/PDA. Status is static client-side config.
