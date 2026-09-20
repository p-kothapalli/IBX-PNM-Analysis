# CRED-2: Productionize the Tile Board Shell (prmCredTileBoard / Card / Progress)

> **Epic:** [Initial Credentialing Review — Tile Dashboard](EPIC_Initial_Cred_Review_Tile_Dashboard.md) · **Priority:** Critical · **Depends on:** CRED-1 · **Blocks:** CRED-12, CRED-13

## Story
**Persona:** Credentialing Specialist (reviewer)

**As a** credentialing specialist,
**I want** a tile dashboard on the Case Manager that shows every verification area with a live status badge and progress, and opens the right editor when I click a tile,
**So that** I can complete the initial credentialing review in any order, pause and resume, and see what is left.

## Scope
In scope:
- Productionize the POC bundles `prmCredTileBoard`, `prmCredTileCard`, `prmCredTileProgress`.
- **Remove** the demo self-guard (`ALLOWED_USER_ID`) — visibility comes from the permission set + App Builder.
- Render tiles **generically from CMDT** via `PRM_VerificationReviewController.getReviewState` (status badges: Pending / In Progress (client-transient) / Completed / Needs Attention / Coming Soon).
- Launch routing: available tile -> console subtab of `PRM_LaunchTarget__c` (off-console -> `NavigationMixin.Navigate`); unavailable -> "Coming Soon" toast; on subtab focus-return, re-call `getReviewState` to refresh.
- Progress header bound to the controller's rollup.
- Placement on the Case Manager (`IndividualApplication`) record page (own FlexiPage/region — no edit to the existing page).

Out of scope: any specific tile's field mapping/record (tile stories), Final Submit (CRED-12).

## Acceptance Criteria

Scenario 1 - Board renders tiles from CMDT with derived status
Given a Case Manager with several verification fields populated
When the specialist opens the board
Then a responsive grid renders one card per active CMDT tile with the derived status badge and a progress header showing "X of Y completed"

Scenario 2 - Clicking an available tile opens its editor scoped to the record
Given a tile whose `PRM_LaunchTarget__c` = 'c__prmLaunchCredentialsAction'
When the specialist clicks it in a console app
Then the existing Credentials action center opens as a focused subtab scoped to the same recordId, with no modification to that component

Scenario 3 - Re-clicking focuses the existing subtab
Given the Credentials editor subtab is already open for this record
When the specialist clicks the tile again
Then the existing subtab is focused rather than a duplicate opened

Scenario 4 - Status refreshes on return
Given the specialist set `PRM_LicenseVerification__c` = 'Data Looks Good' in the editor
When they return to the board tab
Then the License tile badge updates to Completed and progress increments

Scenario 5 - Coming Soon tile
Given a tile with `PRM_Available__c` = false
When the specialist clicks it
Then a "Coming Soon" info toast appears and no navigation occurs

Scenario 6 - Off-console fallback
Given the board renders on a non-console app page
When the specialist clicks an available tile
Then it navigates via a `standard__component` page reference passing `c__recordId`

Scenario 7 - No self-guard
Given any user with the `PRM_CredTileDashboard_Access` permission set
When they open the Case Manager page
Then the board renders (no hardcoded user-Id gate)

## Technical Section
- Keep the copied `openOrFocusSubtab`/`findExistingSubtab`/`buildPageReference` helpers from the POC (reuse-by-reference of `prmGenericButtonLauncher` logic).
- Replace the static `TILE_CONFIG` constant with data from `getReviewState` (wire + `refreshApex` on focus return).
- Embed read-only `prmPractitionerSummary` at top.
- `prmCredTileCard`: `@api tile` -> badge per status, Coming-Soon ribbon, ARIA role/tabindex, `tileselect` on click + Enter/Space.
- `prmCredTileProgress`: `@api completed/total/reviewerName/lastSaved`, SLDS bar, zero-safe.
- IBX brand tokens per `Mockup_Brand_Style_Guide.md`.

## Impact Analysis
- Reuses the deployed POC bundles; converts demo -> production.
- Depends on CRED-1's controller + CMDT contract.
- No edits to action centers or the existing record page.
- Enables end-to-end integration testing for every tile story.

## Clarification Questions
- Confirm final placement: new dedicated FlexiPage vs. add component to the existing record page via App Builder (no metadata edit). Recommend App Builder placement on the shared page gated by permission set.
- Should "In Progress" be shown at all (transient, client-only) or omitted for v1? Recommend show while a tile's editor subtab is open this session.

## Estimated Effort
_AI-estimated — validate with team._

| Component | Effort | Notes |
|-----------|--------|-------|
| `prmCredTileBoard` (wire to controller, launch, refresh) | 2.5d | incl. remove self-guard |
| `prmCredTileCard` / `prmCredTileProgress` polish | 1d | badges, ARIA, brand |
| FlexiPage/placement + Jest | 0.5d | >=85% |
| **Total** | **4d** | Wave 1 |
