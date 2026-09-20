# CRED-7: CAQH Read-Only Compare Surface

> **Epic:** [Initial Credentialing Review — Tile Dashboard](EPIC_Initial_Cred_Review_Tile_Dashboard.md) · **Priority:** Medium · **Depends on:** CRED-1 · **Parallel with:** all other Wave-1 tiles

## Story
**Persona:** Credentialing Specialist (reviewer)

**As a** credentialing specialist,
**I want** a CAQH Compare tile that shows CAQH data read-only beside the Salesforce data,
**So that** I can verify Salesforce records against the CAQH source of truth without editing CAQH.

## Scope
In scope: one `PRM_CredTile_Config__mdt` record (caqh) launching the existing `c__prmAppReviewCaqhMatch` (and/or `c__prmCaqhProfile`) read-only compare.
Out of scope: any change to `prmAppReviewCaqhMatch`/`prmCaqhProfile`/`PRM_AppReviewMatchController`; the board; the controller.

## Acceptance Criteria

Scenario 1 - CAQH tile opens the read-only compare scoped to the record
Given the caqh tile config with `PRM_LaunchTarget__c` = 'c__prmAppReviewCaqhMatch'
When the specialist clicks the CAQH Compare tile
Then the CAQH match/compare opens scoped to the same Case Manager, read-only, with no edits to that component

Scenario 2 - CAQH data is never editable
Given the CAQH compare is open
When the specialist views CAQH-sourced fields
Then those fields are read-only

Scenario 3 - CAQH tile status is informational
Given the caqh tile has no verification picklist
When the board derives status
Then the tile shows an informational/available state (not blocking Final Submit)

## Technical Section
- Record: caqh -> blank `PRM_SourceField__c`, `PRM_Required__c` = false, `PRM_LaunchTarget__c` = `c__prmAppReviewCaqhMatch`, available.
- Note existing CAQH components may be user-gated in the org (`prmAppReviewCaqhMatch`) — confirm gating for pilot reviewers.

## Impact Analysis
- Config + reuse only; parallel-safe.

## Clarification Questions
- Use `prmAppReviewCaqhMatch` (scoring/compare) or `prmCaqhProfile` (profile viewer) as the CAQH tile target — or both? — [VERIFY].
- Confirm any user-gating on the CAQH component is opened for pilot reviewers — [VERIFY].

## Estimated Effort
_AI-estimated — validate with team._

| Component | Effort | Notes |
|-----------|--------|-------|
| 1 CMDT record | 0.5d | mapping + gating check |
| Integration check | 1d | CAQH data loads read-only |
| **Total** | **1.5d** | Wave 1 |
