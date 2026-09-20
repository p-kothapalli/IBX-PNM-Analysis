# CRED-10: Contract Status Tile (net-new, NPI + network)

> **Epic:** [Initial Credentialing Review — Tile Dashboard](EPIC_Initial_Cred_Review_Tile_Dashboard.md) · **Priority:** Medium · **Depends on:** CRED-1 · **Parallel with:** all other Wave-1 tiles

## Story
**Persona:** Credentialing Specialist (reviewer)

**As a** credentialing specialist,
**I want** a Contract Status tile to review/confirm contract status with NPI validation and network assignment,
**So that** I can complete the contract-status verification from the dashboard.

## Scope
In scope: net-new LWC `prmCredTileContractStatus` (contract status + NPI auto-validation + network assignment) + one `PRM_CredTile_Config__mdt` record mapped to `PRM_ContractStatus__c`.
Out of scope: the board; the controller.

## Acceptance Criteria

Scenario 1 - Contract Status tile renders current status
Given a practitioner with a contract/PractitionerRole
When the specialist opens the Contract Status tile
Then current contract status renders

Scenario 2 - NPI auto-validation runs
Given the specialist enters/confirms an NPI
When validation runs
Then an invalid NPI surfaces an inline error and a valid NPI is accepted

Scenario 3 - Status derives from PRM_ContractStatus__c
Given `PRM_ContractStatus__c` resolves to a completed value
When the board derives status
Then the Contract Status tile shows Completed

Scenario 4 - Network assignment persists
Given the specialist assigns a network
When they save
Then the assignment persists with one bulk DML

## Technical Section
- Reuse `PRM_GroupNpiValidationService` (or the address action center's NPI validation) by reference where possible.
- Record: contractStatus -> `PRM_ContractStatus__c` (required), `PRM_TileComponent__c` = `prmCredTileContractStatus`, `PRM_LaunchTarget__c` blank, available.

## Impact Analysis
- Net-new LWC (own bundle) + own CMDT record — parallel-safe.

## Clarification Questions
- Confirm Contract/PractitionerRole objects + network assignment target + NPI validation reuse — [VERIFY].
- Confirm `PRM_ContractStatus__c` completed values — [VERIFY].

## Estimated Effort
_AI-estimated — validate with team._

| Component | Effort | Notes |
|-----------|--------|-------|
| `prmCredTileContractStatus` + Jest | 1.25d | status + NPI + network |
| CMDT record | 0.25d | mapping |
| **Total** | **1.5d** | Wave 1 |
