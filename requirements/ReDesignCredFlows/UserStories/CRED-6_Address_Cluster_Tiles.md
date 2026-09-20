# CRED-6: Address Cluster Tiles (Group/Practice, Address Verification)

> **Epic:** [Initial Credentialing Review — Tile Dashboard](EPIC_Initial_Cred_Review_Tile_Dashboard.md) · **Priority:** High · **Depends on:** CRED-1 · **Parallel with:** all other Wave-1 tiles

## Story
**Persona:** Credentialing Specialist (reviewer)

**As a** credentialing specialist,
**I want** the Group/Practice and Address Verification tiles to open the existing Address action center (with its Add-New-Location wizard),
**So that** I can verify practice locations — including cases with 100+ addresses — from the dashboard.

## Scope
In scope: two `PRM_CredTile_Config__mdt` records (groupPractice, address) launching `c__prmLaunchAddressAction`; validation that the address flow handles high volume (pagination/async already in the action center).
Out of scope: any change to `prmLaunchAddressAction`/`PRM_AddNewLocationUtility`/`PRM_PreciselyAddressService`; the board; the controller.

## Acceptance Criteria

Scenario 1 - Address tile launches the Address action center scoped to the record
Given the address tile config with `PRM_LaunchTarget__c` = 'c__prmLaunchAddressAction'
When the specialist clicks the Address tile
Then the Address action center opens scoped to the same Case Manager with no edits

Scenario 2 - High-volume address set loads without timeout
Given a practitioner with 100+ addresses
When the specialist opens the Address tile
Then the action center paginates/loads addresses without error (existing async behavior)

Scenario 3 - Group/Practice status derivation
Given the group/practice source field resolves to a completed value
When the board derives status
Then the Group/Practice tile shows Completed

Scenario 4 - Address status derivation
Given the address completion signal is satisfied
When the board derives status
Then the Address tile shows Completed (else Pending / Needs Attention)

## Technical Section
- Records: groupPractice -> `PRM_ContractStatus__c` / Service Area `[VERIFY]` (required); address -> Service Area PSV / data-presence `[VERIFY]` (required).
- Both `PRM_LaunchTarget__c` = `c__prmLaunchAddressAction`, available.
- This is the HIGH-complexity tile per the design (100+ addresses) — rely on the action center's existing pagination/async; do not reimplement.

## Impact Analysis
- Config + reuse only; no code edits. Parallel-safe.
- Highest QA attention for volume/perf during CRED-13.

## Clarification Questions
- Confirm completion signal for Group/Practice and Address (which field(s)) — [VERIFY].
- Confirm the address action center's async/pagination thresholds meet the perf target (page load < 3s) — [VERIFY] in CRED-13.

## Estimated Effort
_AI-estimated — validate with team._

| Component | Effort | Notes |
|-----------|--------|-------|
| 2 CMDT records + derivation | 1.5d | mapping |
| High-volume validation | 2d | 100+ addresses, perf |
| Integration checks | 0.5d | via CRED-2 |
| **Total** | **4d** | Wave 1 (largest tile) |
