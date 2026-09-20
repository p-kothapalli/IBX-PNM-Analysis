# Prod-Ready Build Prompt — Credentialing Tile-Dashboard POC

> Paste the block below into Claude (Cursor agent) to build the POC. It is self-contained: it states the goal, the **exact existing assets to reuse**, the new artifacts to create, the conventions to follow, and the acceptance gates. It deliberately forbids rebuilding what already exists.

---

## PROMPT

You are building a **demo POC** in this Salesforce repo that proves a tile-based redesign of the **combined Initial Credentialing Review flow** (Application Review + Initial Cred PSV, merged per the master plan v2.0). **Maximize reuse of existing components — do not rebuild editing UI that already exists.**

### ⛔ STRICT RULE — NO EDITS TO EXISTING COMPONENTS (NON-NEGOTIABLE)
This is a demo. You may **reuse existing components, Apex classes, objects, and fields ONLY by reference** — i.e. by *launching* them (console subtab / navigation), *importing* their Apex methods, or *copying* their patterns into brand-new files. You must **NOT** modify, edit, refactor, rename, re-version, or add targets/fields/methods to **any existing artifact** (`.cls`, `.js`, `.html`, `.css`, `.js-meta.xml`, object/field metadata, permission sets, flexipages, layouts that already exist). Every change you make must live in a **new** file you create. If a reuse path appears to require editing an existing component, **STOP and ask** — do not edit it. Touching an existing component is a hard failure of this task.

### 0. Read first (context)
- `requirements/ReDesignCredFlows/MASTER_Development_Plan_Credentialing_LWC_Redesign.md` (vision)
- `requirements/ReDesignCredFlows/POC_Audit_And_Reuse_Map.md` (what already exists — authoritative reuse list)
- `requirements/ReDesignCredFlows/POC_Execution_Plan.md` (phases, tasks, acceptance criteria — build to this)
- `.cursor/skills/salesforce-development/SKILL.md` and the LWC best-practices rule (mandatory conventions)
- Use the **code-review-graph MCP tools first** (`semantic_search_nodes`, `query_graph`) before Grep/Read when exploring.

### 1. Goal
Build a thin **tile dashboard** on the Case Manager (`IndividualApplication`) record that:
1. Shows a tile grid with live status badges (Pending / In Progress / Completed / Error) and a progress header (X/Y complete, last saved, reviewer).
2. On tile click, opens the matching **existing action center** scoped to the same `recordId`.
3. Persists tile completion status to new custom objects so the reviewer can **pause and resume**.
4. Shows CAQH data read-only beside editable Salesforce data on a CAQH tile.

### 2. REUSE — do NOT recreate these (already deployed in `force-app/main/default`)
- Action centers (the editable tiles): `prmLaunchCredentialsAction` (BusinessLicense), `prmLaunchContactAction` (contacts), `prmLaunchProviderAction` (provider identity / languages / pronouns / affirming care / practitioner info), `prmLaunchAddressAction` (locations + Add-New-Location wizard).
- Apex controllers behind them (reuse as-is): `PRM_BusinessLicenseController`, `PRM_ContactInformationController`, `PRM_ProviderInformationController`, `PRM_AddNewLocationUtility`, `PRM_PreciselyAddressService`, `PRM_GroupNpiValidationService`, `PRM_ActiveLocationsController` (`getPractitionerSummary`).
- CAQH compare: `prmAppReviewCaqhMatch` + `PRM_AppReviewMatchController` + `PRM_CAQHMatchScoreService`.
- Shared building blocks: `prmPractitionerSummary`, `prmNotesCapture`, `prmGenericInlineError`, `prmGenericConfirmModal`, `prmGenericPagination`, `prmGenericSearchInput`, `prmEnhancedDatatable`, `prmMultiSelect`.
- **Subtab launch pattern:** **copy** (do not edit) the console open/focus logic from `prmGenericButtonLauncher.js` (`openOrFocusSubtab`, `findExistingSubtab`, `buildPageReference`, `platformWorkspaceApi` imports) **into your new dashboard component**. Action centers are `lightning__UrlAddressable` and read `c__recordId` from page state — this launch path works **without modifying** any action center.

### 3. CREATE — new artifacts (only these)
**Custom objects**
- `PRM_VerificationSession__c` — OWD Private, Auto-Number Name `VS-{0000000}`. Fields: `PRM_CaseManager__c` (Lookup→IndividualApplication), `PRM_FlowType__c` (restricted picklist: InitialCredReview, ReCredPSVReview, InitialCredQCReview, ReCredPSVQCReview, PDAQCReview — `InitialCredReview` is the combined App Review + PSV flow), `PRM_Status__c` (In Progress[def]/Completed/Abandoned), `PRM_LastAccessedBy__c` (Lookup→User), `PRM_LastAccessedDate__c` (DateTime), `PRM_CompletedTileCount__c` (Number 3,0), `PRM_TotalTileCount__c` (Number 3,0).
- `PRM_VerificationTileStatus__c` — Master-Detail→`PRM_VerificationSession__c` (reparent=false), Auto-Number `VTS-{0000000}`. Fields: `PRM_TileId__c` (Text 80), `PRM_TileLabel__c` (Text 120), `PRM_Status__c` (Pending[def]/In Progress/Completed/Error), `PRM_CompletedBy__c` (Lookup→User), `PRM_CompletedDate__c` (DateTime), `PRM_Notes__c` (LongTextArea), `PRM_ModifiedAfterCompletion__c` (Checkbox).
- **Do NOT** store field-level draft JSON — the action centers commit their own data; this tracks status only.

**Apex** — `PRM_VerificationSessionController` (`with sharing`, all `@AuraEnabled`, CRUD/FLS via `WITH USER_MODE` or `Security.stripInaccessible`, bulk-safe, no SOQL/DML in loops):
- `getOrCreateSession(Id caseManagerId, String flowType)` → returns session + tile statuses (creates session + seeds tile rows from the tile config if none exist).
- `getTileStatuses(Id sessionId)`
- `markTileComplete(Id sessionId, String tileId, String notes)` and `upsertTileStatus(...)` → recompute `PRM_CompletedTileCount__c` in a single update.
- Companion `PRM_VerificationSessionControllerTest` — test-data factory (no `SeeAllData`), bulk + single + negative, assert outcomes, ≥85% coverage.

**LWC** (camelCase folders, SLDS, Lightning base components, `@wire` error handling, Jest tests, ≥85%):
- `prmVerificationTile` — presentational. `@api tile` ({id,label,iconName,status}); status badge; emits `tileselect` with tileId on click.
- `prmProgressHeader` — presentational. `@api completed`, `@api total`, `@api lastSaved`, `@api reviewerName`; SLDS progress bar.
- `prmVerificationDashboard` — container. `@api recordId`; on load call `getOrCreateSession` then render `prmPractitionerSummary` + `prmProgressHeader` + tile grid (`prmVerificationTile` per tile); on `tileselect`, open the mapped action center as a console subtab (reuse the launcher pattern), passing `c__recordId=recordId`; refresh tile statuses on `connectedCallback` and on workspace focus return. Tile→component map is a module constant (see §4). Outside console, fall back to `NavigationMixin.Navigate`.

**Config**
- Permission set `PRM_CredTileDashboard_Access` — R/C/E on the 2 new objects + FLS on FLS-eligible fields; assignable.
- FlexPage placement of `prmVerificationDashboard` on the `IndividualApplication` record page (add `lightning__RecordPage` target to the bundle).

### 4. Tile configuration (Initial Credentialing Review — COMBINED POC)
> App Review + Initial Cred PSV are merged into one **Initial Credentialing Review** flow (`PRM_FlowType__c = InitialCredReview`, 17 tiles). Wire the 5 reusable action centers; the rest are "Coming Soon" placeholders for the POC.

Define this map in `prmVerificationDashboard`:
| tileId | label | target | reuse |
|---|---|---|---|
| practitionerInfo | Practitioner Info | `c__prmLaunchProviderAction` | reuse |
| credentials | License (SBRD) | `c__prmLaunchCredentialsAction` | reuse |
| contact | Contact Information | `c__prmLaunchContactAction` | reuse |
| address | Address / Locations | `c__prmLaunchAddressAction` | reuse |
| caqh | CAQH Compare | `c__prmAppReviewCaqhMatch` | reuse |
| taxonomy, education, dea, cds, workHistory, malpractice, groupPractice, demographics, languages, boardCert, contractStatus, fileUpload, finalSubmit | (combined-flow remainder) | — | **read-only / "Coming Soon" placeholder for POC** |

### 5. Conventions (hard requirements)
- `PRM_` prefix on objects/fields/Apex; PascalCase Apex, camelCase LWC; tests `<Class>Test`.
- Bulkify; one bulk DML per object type; `with sharing`; enforce CRUD/FLS; no hardcoded Ids; resolve record types via cached describe.
- LWC: SLDS utility classes for layout, component CSS for custom styles; ARIA on interactive elements; no `innerHTML`/`document`/`window` DOM hacks; assert DOM/events in Jest (not internal props).
- Deploy order: objects → permission set → Apex → LWC → FlexPage. Set `apiVersion` on **new** bundles only — never re-version existing ones.

### 6. Acceptance gates (must pass before "done")
1. Dashboard renders tile grid + progress header on a Case Manager record.
2. Each reuse tile opens its existing action center scoped to the right `recordId`.
3. Saving in an action center → tile status flips to Completed → progress updates on return.
4. Reload the dashboard → prior statuses resume (pause/resume proven).
5. CAQH tile shows CAQH read-only beside editable SF data.
6. ≥85% Apex + Jest coverage; clean deploy to the target org.

### 7. Do NOT
- **Do not edit, refactor, rename, re-version, or add anything to ANY existing component, Apex class, object, field, permission set, flexipage, or layout.** Reuse strictly by reference (launch / import / copy-into-new-file). If reuse seems to need an edit, STOP and ask. (See the STRICT RULE at the top.)
- Do not build `ApplicationReviewController`, `PSVReviewController`, new contact/license/provider/address editors, or duplicate CAQH UI — reuse the existing ones.
- Do not implement auto-save or field-level draft JSON (out of scope).
- Do not build QC (`prm_qcWrapper`) or PDA QC networks/directory components.
- Do not commit, push, or open a PR unless explicitly asked.

### 8. Deliverables
- All new metadata under `force-app/main/default/` (objects, classes, lwc, permissionsets, flexipages).
- Passing Apex + Jest tests.
- A short `requirements/ReDesignCredFlows/POC_Build_Notes.md` summarizing what was created, what was reused, deploy steps, and the demo script.

Work in dependency order, write tests alongside code, run lints, and stop to confirm any of the Open Questions in `POC_Execution_Plan.md` §7 (target org, embed model, tile sign-off) before deploying.
