# CRED-3: Credentials Cluster Tiles (Education, License, DEA, CDS, Board Certification)

> **Epic:** [Initial Credentialing Review — Tile Dashboard](EPIC_Initial_Cred_Review_Tile_Dashboard.md) · **Priority:** High · **Depends on:** CRED-1 · **Parallel with:** CRED-2, CRED-4..CRED-12

## Story
**Persona:** Credentialing Specialist (reviewer)

**As a** credentialing specialist,
**I want** the Education, License, DEA, CDS and Board Certification tiles to open the existing Credentials action center and reflect my verification decision,
**So that** I can verify all credential documents from the dashboard without a separate OmniScript.

## Scope
In scope: five `PRM_CredTile_Config__mdt` **records** (education, license, dea, cds, boardCert), each mapping to its verification field and launching `c__prmLaunchCredentialsAction`.
Out of scope: any change to `prmLaunchCredentialsAction`/`PRM_BusinessLicenseController` (reuse-by-reference only); the board; the controller.

## Acceptance Criteria

Scenario 1 - License tile launches the Credentials editor scoped to the record
Given the license tile config with `PRM_LaunchTarget__c` = 'c__prmLaunchCredentialsAction'
When the specialist clicks the License tile
Then the Credentials action center opens scoped to the same Case Manager with no edits to that component

Scenario 2 - License status derives from PRM_LicenseVerification__c
Given the specialist sets `PRM_LicenseVerification__c` = 'Data Looks Good' in the editor
When they return to the board
Then the License tile shows Completed

Scenario 3 - Issue Found derives Needs Attention
Given `PRM_LicenseVerification__c` = 'Issue Found'
When the board derives status
Then the License tile shows Needs Attention

Scenario 4 - Education / DEA / CDS / Board Cert render with correct sequence and required flags
Given the five credentials CMDT records are deployed
When the board loads
Then Education, License, DEA, CDS and Board Certification tiles appear at their configured sequence with correct required flags

## Technical Section
- Records (one file each) under `customMetadata/PRM_CredTile_Config.<tileId>.md-meta.xml`:
  - education -> `PRM_EducationVerification__c` (required)
  - license -> `PRM_LicenseVerification__c` (required)
  - dea -> `PRM_DEAVerification__c` (optional)
  - cds -> `PRM_CDSVerification__c` (optional)
  - boardCert -> Board Certification PSV field `[VERIFY]` (conditional)
- `PRM_CompletedValues__c` = `Data Looks Good`; `PRM_AttentionValues__c` = `Missing Information,Issue Found,Unable to Proceed`.
- `PRM_LaunchTarget__c` = `c__prmLaunchCredentialsAction`, `PRM_Available__c` = true.

## Impact Analysis
- Pure config (CMDT records) + reuse of an existing editor; no code edits.
- Parallel-safe: only this story's five record files are added.

## Clarification Questions
- Confirm the Board Certification source field API name and whether the tile is always shown or `showWhen` Re-Cred/applicable — [VERIFY].
- Confirm the Credentials action center already exposes Education + Board Cert tabs (audit says yes) — [VERIFY].

## Estimated Effort
_AI-estimated — validate with team._

| Component | Effort | Notes |
|-----------|--------|-------|
| 5 CMDT records + validation | 1.5d | mapping + status derivation checks |
| Jest/board integration checks | 0.5d | via CRED-2 once merged |
| **Total** | **2d** | Wave 1 |
