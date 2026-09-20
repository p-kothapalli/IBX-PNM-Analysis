# Build Prompt — Credentialing Tile UI (UI Components Only, Case Manager Layout)

> Paste the block below into Claude (Cursor agent). It builds **only the UI components** of the tile dashboard to drop on the Case Manager (`IndividualApplication`) record layout. It builds **no backend** and **edits nothing** that already exists. Build to `POC_UI_Components_Execution_Plan.md`.

---

## PROMPT

You are building the **UI components only** of a tile-based credentialing dashboard to add to the **Case Manager (`IndividualApplication`) record page** in this Salesforce repo. This is a visual demo: it reuses existing editors by *launching* them, but builds no backend and modifies nothing that already exists.

### ⛔ STRICT RULE — NO EDITS TO EXISTING COMPONENTS (NON-NEGOTIABLE)
You may reuse existing components, Apex, objects, and fields **ONLY by reference** — launch them (console subtab / navigation), import their Apex (read-only, if needed), or copy their patterns into **new** files. You must **NOT** modify, edit, refactor, rename, re-version, extend, or add targets/fields/methods to **any existing artifact** (`.cls`, `.js`, `.html`, `.css`, `.js-meta.xml`, objects, fields, permission sets, flexipages, layouts). **Every change must be a NEW file.** Before finishing, run `git status` and `git diff --stat` and confirm the diff shows **only new files** — if any existing file changed, revert it. If reuse appears to need an edit, STOP and ask. Touching an existing component is a hard failure.

### 0. Read first
- `requirements/ReDesignCredFlows/POC_UI_Components_Execution_Plan.md` (authoritative — build to this)
- `requirements/ReDesignCredFlows/POC_Audit_And_Reuse_Map.md` (reusable inventory)
- `.cursor/skills/salesforce-development/SKILL.md` + the LWC best-practices rule
- Use code-review-graph MCP tools first when exploring.

### 1. Goal
A visual tile board for the Case Manager record page that shows a practitioner header, a progress indicator, and a clickable grid of verification tiles. Clicking a "reuse" tile launches the matching **existing** action center (console subtab) scoped to the same record. No persistence, no new Apex, no edits.

### 2. REUSE by reference only (do NOT modify)
- Launch targets (existing `lightning__UrlAddressable`, read `c__recordId` from page state): `c__prmLaunchCredentialsAction`, `c__prmLaunchContactAction`, `c__prmLaunchProviderAction`, `c__prmLaunchAddressAction`, `c__prmAppReviewCaqhMatch`.
- Embed (read-only, as a child tag): `prmPractitionerSummary` (`<c-prm-practitioner-summary record-id={recordId}>`).
- Subtab launch pattern: **copy** `openOrFocusSubtab`, `findExistingSubtab`, `buildPageReference` and the `platformWorkspaceApi` imports from `prmGenericButtonLauncher.js` **into your new board** (copy, never edit the launcher).

### 3. CREATE — new LWCs only (no objects, no Apex)
**`prmCredTileCard`** (presentational)
- `@api tile` = `{ id, label, iconName, status, available }`.
- Renders an SLDS card: icon + label + status badge (Pending / In Progress / Completed / Error styling); show a "Coming Soon" ribbon and a muted look when `available === false`.
- `role="button"`, `tabindex="0"`, `aria-label`; click and Enter/Space emit `tileselect` → `detail: { tileId }`.

**`prmCredTileProgress`** (presentational)
- `@api completed`, `@api total`, `@api lastSaved`, `@api reviewerName`.
- SLDS progress bar + "X of Y completed"; safe when `total === 0`; optional last-saved / reviewer line.

**`prmCredTileBoard`** (container; targets `lightning__RecordPage` and `lightning__AppPage`)
- `@api recordId` (Case Manager `IndividualApplication` Id); also accept `c__recordId` page-state fallback.
- Top: embed `prmPractitionerSummary`.
- Holds the **tile config constant** (§4) + tile→target map; renders `prmCredTileProgress` (counts derived from tile statuses) + a responsive SLDS grid of `prmCredTileCard`.
- On `tileselect`:
  - If `available`: in a console app, open the mapped component as a **subtab** (copied launcher logic) with `state: { c__recordId: this.recordId }` and a friendly tab label; outside console, `this[NavigationMixin.Navigate]` to the `standard__component` page ref.
  - If not `available`: show a "Coming Soon" toast (`ShowToastEvent`, variant info).
- Status mode = **static from config** for the first demo (see plan OQ-UI-2); structure the config so client-side/derived status can be added later without rework.

### 4. Tile config (Initial Credentialing Review — COMBINED demo) — constant in `prmCredTileBoard`
> Business merged Application Review + Initial Cred PSV into one **Initial Credentialing Review** flow (17 tiles). The board demos the **combined** inventory: the 5 reusable action centers are wired (`available: true`); the rest are "Coming Soon" placeholders.

| tileId | label | iconName | available | target |
|---|---|---|---|---|
| practitionerInfo | Practitioner Info | utility:user | true | c__prmLaunchProviderAction |
| taxonomy | Taxonomy & Specialty | utility:product_item | false | — |
| education | Education | utility:education | false | — |
| credentials | License (SBRD) | utility:identity | true | c__prmLaunchCredentialsAction |
| dea | DEA | utility:record | false | — |
| cds | CDS | utility:record | false | — |
| workHistory | Work History | utility:work_order_type | false | — |
| malpractice | Malpractice | utility:shield | false | — |
| groupPractice | Group / Practice | utility:account | false | — |
| address | Address / Locations | utility:location | true | c__prmLaunchAddressAction |
| demographics | Demographics & Diversity | utility:people | false | — |
| languages | Languages Spoken | utility:world | false | — |
| contact | Contact Information | utility:contact_request | true | c__prmLaunchContactAction |
| boardCert | Board Certification | utility:reward | false | — |
| contractStatus | Contract Status | utility:contract | false | — |
| caqh | CAQH Compare | utility:comparison | true | c__prmAppReviewCaqhMatch |
| files | File Upload | utility:upload | false | — |
| finalSubmit | Final Submit | utility:check | false | — |
(Include a demo `status` per tile: a mix of Completed / In Progress / Pending for a realistic-looking board. CAQH Compare can also be surfaced inside Practitioner Info; kept as its own tile here for the demo.)

### 5. Placement
- Create a **new** FlexiPage (e.g. `PRM_CredTileDemo_CaseManager`) of type record page for `IndividualApplication` hosting `prmCredTileBoard`, OR document the App Builder drag-drop step. **Do not edit an existing FlexiPage/layout in place.** (Plan OQ-UI-3.)

### 6. Conventions
- camelCase LWC folders (`prmCredTileBoard`); SLDS utility classes for layout, component CSS for custom styling; Lightning base components; ARIA + keyboard support; `@wire` error handling; set `apiVersion` on **new** bundles only.
- Jest tests for all 3 LWCs (≥85%): assert rendered DOM/badges/events and the launch call (mock `lightning/platformWorkspaceApi` + `lightning/navigation`), not internal props.

### 7. Acceptance gates (must pass)
1. `prmCredTileBoard` renders on a Case Manager record page: practitioner header + progress + tile grid.
2. Tiles show correct status styling; unavailable tiles show "Coming Soon".
3. Clicking a reuse tile opens the mapped action center scoped to the right `recordId` — **with zero edits to it**.
4. ≥85% Jest coverage; clean deploy.
5. `git diff --stat` shows **only new files** (no existing file touched).

### 8. Do NOT
- Do not edit/refactor/rename/re-version/extend any existing component, Apex, object, field, permission set, flexipage, or layout. New files only.
- Do not create custom objects or Apex (UI-only demo — status is static/client-side).
- Do not implement persistence, pause/resume, final submit, QC, or PDA components.
- Do not commit, push, or open a PR unless explicitly asked.

### 9. Deliverables
- 3 new LWC bundles + 1 new FlexiPage (or documented placement) under `force-app/main/default/`.
- Passing Jest tests.
- `requirements/ReDesignCredFlows/POC_UI_Build_Notes.md`: what was created, what was reused (by reference), deploy steps, demo script, and the `git diff --stat` proof of no edits.

Work in order (cards → progress → board → placement), write tests alongside, run lints, and confirm Open Questions (target org, status mode, placement) before deploying.
