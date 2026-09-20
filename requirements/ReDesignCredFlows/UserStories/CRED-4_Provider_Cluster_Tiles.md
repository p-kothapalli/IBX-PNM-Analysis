# CRED-4: Provider Cluster Tiles (Practitioner Info, Demographics & Diversity, Languages)

> **Epic:** [Initial Credentialing Review — Tile Dashboard](EPIC_Initial_Cred_Review_Tile_Dashboard.md) · **Priority:** High · **Depends on:** CRED-1 · **Parallel with:** CRED-2, CRED-3, CRED-5..CRED-12

## Story
**Persona:** Credentialing Specialist (reviewer)

**As a** credentialing specialist,
**I want** the Practitioner Info, Demographics & Diversity, and Languages tiles to open the existing Provider action center,
**So that** I can review identity, diversity and language data from the dashboard.

## Scope
In scope: three `PRM_CredTile_Config__mdt` records (practitionerInfo, demographics, languages) launching `c__prmLaunchProviderAction`.
Out of scope: any change to `prmLaunchProviderAction`/`PRM_ProviderInformationController`; the board; the controller.

## Acceptance Criteria

Scenario 1 - Provider tiles launch the Provider action center
Given a provider-cluster tile with `PRM_LaunchTarget__c` = 'c__prmLaunchProviderAction'
When the specialist clicks it
Then the Provider action center opens scoped to the same Case Manager with no edits

Scenario 2 - Practitioner Info status derives correctly
Given the Practitioner Info source field resolves to a completed value
When the board derives status
Then the Practitioner Info tile shows Completed

Scenario 3 - Demographics and Languages render at configured sequence
Given the three provider CMDT records are deployed
When the board loads
Then Practitioner Info, Demographics & Diversity and Languages appear at their configured order

Scenario 4 - Data-presence derivation for a tile without a picklist
Given the languages tile has a blank `PRM_SourceField__c` (derive-by-presence)
When language records exist for the practitioner
Then the Languages tile shows Completed (else Pending)

## Technical Section
- Records: practitionerInfo (required; `PRM_AttestationVerification__c` or data-presence `[VERIFY]`), demographics (optional; data-presence `[VERIFY]`), languages (optional; data-presence `[VERIFY]`).
- All `PRM_LaunchTarget__c` = `c__prmLaunchProviderAction`, `PRM_Available__c` = true.
- Where data-presence derivation is needed, document the presence check for CRED-1's extension point.

## Impact Analysis
- Config + reuse only; no code edits. Parallel-safe (own record files).

## Clarification Questions
- Confirm the source field vs. data-presence rule for Practitioner Info / Demographics / Languages — [VERIFY].
- Practitioner Info also shows a read-only `prmPractitionerSummary` in the board header (CRED-2) — confirm no duplication concern.

## Estimated Effort
_AI-estimated — validate with team._

| Component | Effort | Notes |
|-----------|--------|-------|
| 3 CMDT records + presence rules | 1.5d | mapping + derivation |
| Integration checks | 0.5d | via CRED-2 |
| **Total** | **2d** | Wave 1 |
