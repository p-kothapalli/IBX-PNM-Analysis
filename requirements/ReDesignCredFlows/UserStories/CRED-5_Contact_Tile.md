# CRED-5: Contact Information Tile

> **Epic:** [Initial Credentialing Review — Tile Dashboard](EPIC_Initial_Cred_Review_Tile_Dashboard.md) · **Priority:** Medium · **Depends on:** CRED-1 · **Parallel with:** all other Wave-1 tiles

## Story
**Persona:** Credentialing Specialist (reviewer)

**As a** credentialing specialist,
**I want** the Contact Information tile to open the existing Contact action center,
**So that** I can verify practitioner contact details from the dashboard.

## Scope
In scope: one `PRM_CredTile_Config__mdt` record (contact) launching `c__prmLaunchContactAction`.
Out of scope: any change to `prmLaunchContactAction`/`PRM_ContactInformationController`; the board; the controller.

## Acceptance Criteria

Scenario 1 - Contact tile launches the Contact editor scoped to the record
Given the contact tile config with `PRM_LaunchTarget__c` = 'c__prmLaunchContactAction'
When the specialist clicks the Contact tile
Then the Contact action center opens scoped to the same Case Manager with no edits

Scenario 2 - Contact status derives from data presence
Given a primary contact exists for the practitioner
When the board derives status
Then the Contact tile shows Completed

Scenario 3 - No contact yet derives Pending
Given no verified contact exists
When the board derives status
Then the Contact tile shows Pending

## Technical Section
- Record: contact -> `PRM_SourceField__c` blank (derive by presence `[VERIFY]`), `PRM_LaunchTarget__c` = `c__prmLaunchContactAction`, optional, available.

## Impact Analysis
- Config + reuse only; parallel-safe.

## Clarification Questions
- Confirm the completion signal for Contact (a verification field vs. contact-record presence) — [VERIFY].

## Estimated Effort
_AI-estimated — validate with team._

| Component | Effort | Notes |
|-----------|--------|-------|
| 1 CMDT record + derivation | 0.75d | mapping |
| Integration check | 0.25d | via CRED-2 |
| **Total** | **1d** | Wave 1 |
