# CRED-1: Foundation — Tile-Config CMDT, Read-Model Controller, Permission Set

> **Epic:** [Initial Credentialing Review — Tile Dashboard](EPIC_Initial_Cred_Review_Tile_Dashboard.md) · **Priority:** Critical · **Depends on:** none (start immediately) · **Blocks:** all other stories

## Story
**Persona:** Credentialing Platform Developer

**As a** credentialing platform developer,
**I want** a tile-config Custom Metadata type, a read-model Apex controller that derives tile status from existing Case Manager fields, and a permission set,
**So that** every downstream tile and the board can be built in parallel against a stable contract with no new custom objects and no backfill.

## Scope
In scope:
- `PRM_CredTile_Config__mdt` custom metadata **type** (fields per Epic §2) — the type only; individual tile **records** are added by the tile stories (CRED-3..CRED-11).
- `PRM_VerificationReviewController` (`with sharing`): `getReviewState(Id caseManagerId)` returning per-tile derived status + progress; optional `getVerificationHistory(Id caseManagerId)`.
- `PRM_CredTileDashboard_Access` permission set: Apex class access + FLS read on the `IndividualApplication` verification/PSV/outcome fields, edit on `PRM_PSVOutcome__c`.
- Seed CMDT records for the `finalSubmit` tile only is NOT in scope (CRED-12 owns it).

Out of scope: the board LWC (CRED-2), any tile records/LWCs, the `submitCredentialingReview` method (CRED-12), new objects (explicitly none — see D-6).

## Acceptance Criteria

Scenario 1 - Positive verification value derives Completed
Given a `PRM_CredTile_Config__mdt` record whose `PRM_SourceField__c` = 'PRM_LicenseVerification__c' and `PRM_CompletedValues__c` contains 'Data Looks Good'
And an IndividualApplication with `PRM_LicenseVerification__c` = 'Data Looks Good'
When `getReviewState` is called for that record
Then the corresponding tile status resolves to 'Completed'

Scenario 2 - Blank source field derives Pending
Given a tile config whose `PRM_SourceField__c` = 'PRM_LicenseVerification__c'
And an IndividualApplication where `PRM_LicenseVerification__c` is blank
When `getReviewState` is called
Then the tile status resolves to 'Pending'

Scenario 3 - Attention value derives Needs Attention
Given a tile config whose `PRM_AttentionValues__c` contains 'Issue Found'
And an IndividualApplication with that source field = 'Issue Found'
When `getReviewState` is called
Then the tile status resolves to 'Needs Attention'

Scenario 4 - Progress rollup counts completed tiles
Given 17 active tile configs of which 5 resolve to Completed
When `getReviewState` is called
Then the returned progress reports completed = 5 and total = 17

Scenario 5 - Historical case with no prior tile store still renders
Given an IndividualApplication created before this feature (no session records ever existed)
When `getReviewState` is called
Then statuses are derived correctly from its existing field values with no backfill required

Scenario 6 - FLS enforced
Given a running user without read access to a source verification field
When `getReviewState` is called
Then the query runs in user mode and the inaccessible field does not leak a value

## Technical Section
- **CMDT type** `PRM_CredTile_Config__mdt` with fields listed in Epic §2. Restricted where sensible; `PRM_SourceField__c` stores an `IndividualApplication` field API name.
- **Controller**: read active CMDT records via `PRM_CredTile_Config__mdt.getAll()`; collect distinct non-blank `PRM_SourceField__c`; build **one** dynamic SOQL (`SELECT <fields> FROM IndividualApplication WHERE Id = :caseManagerId WITH USER_MODE`). Derive status per tile: value in `PRM_CompletedValues__c` -> Completed; in `PRM_AttentionValues__c` -> Needs Attention; blank -> Pending; tiles with blank `PRM_SourceField__c` -> derive from data presence hook (returns Pending by default, overridden by net-new tiles' own logic in later stories via a documented extension point or a `PRM_TileComponent__c` self-report).
- Return a typed wrapper (`List<TileState>` with tileId, label, icon, sequence, required, status, launchTarget, available) + `ProgressState` (completed, total).
- `getVerificationHistory` queries `IndividualApplicationHistory` (Field, OldValue, NewValue, CreatedById, CreatedDate) for the audit trail; note async creation latency.
- Bulk-safe, no SOQL in loops, cacheable where side-effect-free.

## Impact Analysis
- **No new objects**; reads existing `IndividualApplication` fields already written by current flows.
- No changes to existing components, action centers, IPs, or the Case Manager page.
- Establishes the contract every other story codes against; therefore it is the sole Wave-0 item and must merge before Wave 1.
- Field-history reads depend on `trackHistory=true` (already set on the verification fields).

## Clarification Questions
- Confirm the current **history-tracked field count** on `IndividualApplication` (20-field cap headroom) — [VERIFY].
- Confirm the canonical **completed** vs **attention** picklist values per field family (are all "positive" values exactly `Data Looks Good`, or do some fields use `Verified`?) — [VERIFY].
- Should `getReviewState` be `cacheable=true` (better perf, needs refreshApex on return) or not (always fresh)? Recommend cacheable + `refreshApex`.

## Estimated Effort
_AI-estimated — validate with team._

| Component | Effort | Notes |
|-----------|--------|-------|
| `PRM_CredTile_Config__mdt` type | 0.5d | fields + deploy |
| `PRM_VerificationReviewController` + test | 2d | dynamic derivation, progress, history, >=85% |
| `PRM_CredTileDashboard_Access` | 0.5d | FLS + class access |
| **Total** | **3d** | Wave 0 — blocks everything |
