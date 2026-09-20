# Credentialing Tile UI — Demo Execution Plan (UI Components Only)

> **STATUS: PROPOSAL — awaiting review.** No artifacts are created until reviewed and the Open Questions (§7) are answered.
>
> **Scope:** ONLY the **UI components** of the tile design that drop onto the **Case Manager (`IndividualApplication`) record layout**. This is a presentation-layer demo — it reuses existing editors by *launching* them, but builds **no backend** (no new objects, no new Apex) and **edits nothing** that already exists.
>
> **Companion:** `POC_UI_Components_Claude_Prompt.md` (the build prompt). The fuller persistence-backed version lives in `POC_Execution_Plan.md` (a later phase, not this one).
>
> **Format mirrors** `docs/implementation-plan/Epic_A_Execution_Plan.md` (CONFIRMED / OPEN / RISK / RECOMMENDATION tags).
>
> **Date:** 2026-06-23

> ### ⛔ STRICT RULE — NO EDITS TO EXISTING COMPONENTS
> Every reuse is **by reference only** (launch / navigate / import / copy-pattern-into-new-file). **No existing component, Apex class, object, field, permission set, flexipage, or layout may be edited, refactored, renamed, re-versioned, or extended.** Every change lives in a **new** file. If a path seems to need an edit, STOP and ask. This is a hard constraint for the whole plan.

---

## 1. Objective & scope

### 1.1 Objective
- **[CONFIRMED]** Deliver a **visual tile dashboard** that can be added to the Case Manager (`IndividualApplication`) Lightning record page, showing: a practitioner header, a progress indicator, and a clickable grid of verification tiles. Clicking a tile **launches the matching existing action center** (console subtab) scoped to the same record — proving the look-and-feel and navigation of the redesign with zero backend and zero edits.

### 1.2 In scope (UI only)
- 3 new presentational LWCs: `prmCredTileBoard` (container), `prmCredTileProgress` (header/progress), `prmCredTileCard` (tile).
- 1 new FlexPage (or a record-page region) that hosts `prmCredTileBoard` on `IndividualApplication`.
- Tile definitions as a **client-side config constant** (label, icon, status, target component).
- Reuse-by-reference: launch the 4 action centers + CAQH compare; embed the read-only `prmPractitionerSummary`.

### 1.3 Out of scope (this UI demo)
- **No** `PRM_VerificationSession__c` / `PRM_VerificationTileStatus__c` objects.
- **No** new Apex (status is demo/derived/client-side, not persisted).
- **No** pause/resume persistence, no final-submit aggregation.
- **No** edits to existing action centers, controllers, objects, fields, permission sets, or layouts.
- **No** QC / PDA components.

### 1.4 How tile status works in a UI-only demo
- **[OPEN] OQ-UI-2:** choose one (no backend either way):
  - (a) **Static demo statuses** from the config constant (simplest; great for a screenshot/walkthrough).
  - (b) **Client-side session state** — mark a tile "visited/in-progress" when launched; resets on full reload (no persistence).
  - (c) **Derived (read-only) statuses** computed from existing `cacheable` Apex already used by the action centers (e.g. "Completed" if license/contact data exists) — *import only, no new Apex, no edits*. Slightly more real, still UI-only.
- **[RECOMMENDATION]** Ship (a) for the first demo, with the config shaped so (b)/(c) can layer on later without rework.

---

## 2. Constraints
- **[CONFIRMED]** Follow `.cursor/skills/salesforce-development/SKILL.md` + LWC best-practices: Lightning base components, SLDS for layout, component CSS for custom styles, `@wire` error handling, ARIA on interactive elements, Jest ≥85%, assert DOM/events (not internal props).
- **[CONFIRMED]** `PRM_`-style naming for LWC folders (camelCase, `prmCred*`); new bundles only get `apiVersion`.
- **[CONFIRMED]** `recordId` = the `IndividualApplication` (Case Manager) Id; comes via `@api recordId` on a record page.

---

## 3. Dependencies & prerequisites
- **[CONFIRMED]** Existing action centers + `prmPractitionerSummary` + `prmGenericButtonLauncher` already deployed (verified).
- **[CONFIRMED]** Reuse the subtab-launch pattern by **copying** `prmGenericButtonLauncher.js`'s `openOrFocusSubtab` / `findExistingSubtab` / `buildPageReference` into the new board (no edit to the launcher).
- **[OPEN] OQ-UI-1 — Target org** (alias / scratch vs `ibx--qa`).

---

## 4. Acceptance criteria
- **[CONFIRMED]** AC1: `prmCredTileBoard` renders on a Case Manager record page (added via Lightning App Builder) with practitioner header + progress + tile grid.
- **[CONFIRMED]** AC2: Tiles render distinct status styling (Pending / In Progress / Completed / Error) from config.
- **[CONFIRMED]** AC3: Clicking a "reuse" tile opens the mapped existing action center as a console subtab scoped to the same `recordId` — **with no modification to that action center**.
- **[CONFIRMED]** AC4: Clicking a "placeholder" tile (no existing editor) shows a "Coming Soon" state, not an error.
- **[CONFIRMED]** AC5: Responsive SLDS grid; keyboard-accessible tiles (role/tabindex/aria).
- **[CONFIRMED]** AC6: ≥85% Jest coverage on the 3 LWCs; clean deploy; **git diff shows only new files** (proof of no edits).

---

## 5. Phases, milestones & task breakdown

### Phase 0 — Setup *(M0)*
**T0.1 — Branch** `poc/cred-tile-ui` from `main`. Validation: branch exists.
**T0.2 — Confirm org & status mode ⛔ Pending (OQ-UI-1, OQ-UI-2).**

### Phase 1 — Presentational LWCs *(M1: components render in isolation)*

**T1.1 — `prmCredTileCard`** (pure presentational)
- Purpose: one tile card.
- Outcome: `@api tile` = `{ id, label, iconName, status, available }`; renders SLDS card with status badge + icon; `Coming Soon` ribbon when `available === false`; click + Enter/Space emit `tileselect` (`detail: { tileId }`); `role="button"`, `tabindex="0"`, `aria-label`.
- Deps: none. Validation: Jest — badge class per status, disabled/coming-soon state, event on click + keydown. Risk: none. Completion: covered.

**T1.2 — `prmCredTileProgress`** (pure presentational)
- Purpose: progress header.
- Outcome: `@api completed`, `@api total`, `@api lastSaved`, `@api reviewerName`; SLDS progress bar + "X of Y completed" + optional last-saved/reviewer line; safe when total = 0.
- Deps: none. Validation: Jest — bar width %, zero-state. Completion: covered.

### Phase 2 — Container & launch *(M2: board works on a page)*

**T2.1 — `prmCredTileBoard`** (container, `lightning__RecordPage` + `lightning__AppPage` targets)
- Purpose: assemble header + progress + tile grid and route clicks.
- Outcome:
  - `@api recordId` (Case Manager). Also accept `c__recordId` page-state fallback (for app-page use).
  - Embeds `prmPractitionerSummary` (reuse, read-only) at top.
  - Holds the **tile config constant** (§6) and a tile→target-component map.
  - Renders `prmCredTileProgress` (counts derived from tile config statuses) + a responsive grid of `prmCredTileCard`.
  - On `tileselect`: if the tile is `available`, **launch the mapped action center as a console subtab** (copied launcher logic) passing `c__recordId=recordId`; outside console, `NavigationMixin.Navigate` to the `standard__component` page ref; if not available, show a Coming-Soon toast.
  - (If OQ-UI-2 = b) flip the launched tile's local status to In Progress in component state.
- Deps: T1.1, T1.2. Validation: Jest (mock `platformWorkspaceApi`/navigation; assert subtab open with right component + recordId; assert grid renders N tiles; coming-soon path). Risk: **[RISK]** console vs non-console; **[RISK]** focus-return is not required for a static-status demo. Completion: AC1–AC5.

### Phase 3 — Placement & access *(M3)*
**T3.1 — FlexPage / record-page region** — add `prmCredTileBoard` to the `IndividualApplication` record page (new FlexiPage metadata, or document the App Builder drag-drop step). Validation: renders for a test Case Manager. **[CONSTRAINT]** create a **new** FlexiPage or add to a region without editing existing components; do not modify existing layouts/flexipages in place if that would count as an edit — prefer a new FlexiPage activation for the demo. *(See OQ-UI-3.)*
**T3.2 — Access** — the 3 LWCs need no new object perms. If a new FlexiPage is created, ensure it's assignable to the demo profile/app. Validation: visible to demo user.

### Phase 4 — Deploy, test, demo *(M4: signed off)*
**T4.1 — Validate-only deploy** (⛔ Pending OQ-UI-1).
**T4.2 — Deploy** (LWC → FlexPage) + smoke.
**T4.3 — Demo script** — open a Case Manager → board renders → walk tiles → launch each action center (no edits) → show Coming-Soon tiles.
**T4.4 — Evidence** — Jest coverage, deploy result, **`git status`/`git diff --stat` proving only new files**, demo screenshots/recording.

---

## 6. Tile configuration (Application Review demo)

Client-side constant in `prmCredTileBoard` (no backend):

| tileId | label | iconName | available | target (reuse) |
|---|---|---|---|---|
| credentials | Credentials / License | utility:identity | true | `c__prmLaunchCredentialsAction` |
| contact | Contact Information | utility:contact_request | true | `c__prmLaunchContactAction` |
| provider | Provider & Diversity Info | utility:user | true | `c__prmLaunchProviderAction` |
| address | Address / Locations | utility:location | true | `c__prmLaunchAddressAction` |
| caqh | CAQH Compare | utility:comparison | true | `c__prmAppReviewCaqhMatch` |
| education | Education | utility:education | false | — (Coming Soon) |
| workHistory | Work History | utility:work_order_type | false | — (Coming Soon) |
| malpractice | Malpractice | utility:shield | false | — (Coming Soon) |
| files | File Upload | utility:upload | false | — (Coming Soon) |
| finalSubmit | Final Submit | utility:check | false | — (Coming Soon) |

Each entry also carries a demo `status` (Pending/In Progress/Completed/Error) if OQ-UI-2 = (a).

---

## 7. Open Questions & Decisions Log
- **◻ OQ-UI-1 — Target org** (alias / scratch vs `ibx--qa`) — gates deploy.
- **◻ OQ-UI-2 — Status mode:** (a) static demo / (b) client-side / (c) derived read-only. *Recommend (a).*
- **◻ OQ-UI-3 — Placement:** new dedicated FlexiPage for the demo (recommended; avoids touching existing pages) vs. adding the component to the existing `IndividualApplication` record page via App Builder (manual, no metadata edit). 
- **✅ OQ-UI-4 — Embed model: subtab launch** (modal would require editing action centers — forbidden).

---

## 8. Risk register
| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| U1 | Subtab launch needs console app | Med | Low | `NavigationMixin` fallback off-console |
| U2 | `recordId` not present on app-page context | Low | Low | accept `c__recordId` fallback |
| U3 | Reviewer expects real status without backend | Med | Low | label demo clearly; (c) derived option available |
| U4 | Accidental edit to an existing bundle | Low | High | gate: `git diff --stat` must show only new files (AC6/T4.4) |
| U5 | New FlexiPage activation collides with existing | Low | Med | use a separate demo FlexiPage / app (OQ-UI-3) |
