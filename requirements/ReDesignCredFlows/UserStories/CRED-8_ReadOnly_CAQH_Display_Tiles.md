# CRED-8: Read-Only CAQH-Display Tiles (Work History, Malpractice)

> **Epic:** [Initial Credentialing Review — Tile Dashboard](EPIC_Initial_Cred_Review_Tile_Dashboard.md) · **Priority:** Medium · **Depends on:** CRED-1 · **Parallel with:** all other Wave-1 tiles

## Story
**Persona:** Credentialing Specialist (reviewer)

**As a** credentialing specialist,
**I want** Work History and Malpractice tiles that display CAQH data read-only and let me record a verification decision,
**So that** I can verify these areas that have no existing editor.

## Scope
In scope: two net-new read-only LWCs `prmCredTileWorkHistory`, `prmCredTileMalpractice` (CAQH display + verification decision writing the existing field) and two `PRM_CredTile_Config__mdt` records.
Out of scope: new editors for the underlying data (read-only display only); the board; the controller.

## Acceptance Criteria

Scenario 1 - Work History tile renders CAQH data read-only
Given a practitioner with CAQH work history
When the specialist opens the Work History tile
Then CAQH work-history entries render read-only

Scenario 2 - Setting the verification decision updates status
Given the specialist sets `PRM_WorkHistoryVerification__c` = 'Data Looks Good'
When they return to the board
Then the Work History tile shows Completed

Scenario 3 - Malpractice tile renders and derives status
Given CAQH malpractice coverage data
When the specialist opens the Malpractice tile and sets `PRM_MalpracticeCoverageVerification__c`
Then the Malpractice tile status derives from that field

Scenario 4 - Issue value derives Needs Attention
Given `PRM_WorkHistoryVerification__c` = 'Issue Found'
When the board derives status
Then the Work History tile shows Needs Attention

## Technical Section
- LWCs render CAQH data read-only (reuse `prmCaqhProfile` sections or `PRM_CaqhProfileController` by reference where possible) + a verification picklist + `prmNotesCapture`.
- Writing the verification field: reuse an existing update path or a minimal `@AuraEnabled` update (WITH USER_MODE) — confirm whether an existing controller already updates these IA fields to avoid a new class.
- Records: workHistory -> `PRM_WorkHistoryVerification__c` (optional), malpractice -> `PRM_MalpracticeCoverageVerification__c` (required). `PRM_TileComponent__c` set to the new LWCs; `PRM_LaunchTarget__c` blank (rendered inline / modal, not a reused subtab).

## Impact Analysis
- Net-new LWCs in their own bundles (disjoint) + own CMDT records — parallel-safe.
- May need a tiny update method for the two IA fields; prefer reusing an existing one.

## Clarification Questions
- Is there an existing `@AuraEnabled` method to set these IA verification fields, or is a small new one acceptable? — [VERIFY].
- Confirm Malpractice is required and Work History optional — [VERIFY] against business rules (D-5).

## Estimated Effort
_AI-estimated — validate with team._

| Component | Effort | Notes |
|-----------|--------|-------|
| `prmCredTileWorkHistory` + Jest | 1d | CAQH read-only + decision |
| `prmCredTileMalpractice` + Jest | 0.75d | CAQH read-only + decision |
| 2 CMDT records | 0.25d | mapping |
| **Total** | **2d** | Wave 1 |
