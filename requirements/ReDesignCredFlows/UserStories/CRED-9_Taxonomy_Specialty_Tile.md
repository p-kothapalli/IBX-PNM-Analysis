# CRED-9: Taxonomy & Specialty Verification Tile (net-new)

> **Epic:** [Initial Credentialing Review — Tile Dashboard](EPIC_Initial_Cred_Review_Tile_Dashboard.md) · **Priority:** High · **Depends on:** CRED-1 · **Parallel with:** all other Wave-1 tiles

## Story
**Persona:** Credentialing Specialist (reviewer)

**As a** credentialing specialist,
**I want** a Taxonomy & Specialty tile to review CAQH specialty (read-only), maintain Salesforce taxonomy records, and set the practitioner role,
**So that** I can verify specialties and PCP/Specialist/Dual role in one place.

## Scope
In scope: net-new LWC `prmCredTileTaxonomy` (CAQH specialty read-only + SF taxonomy add/remove/update + Practitioner Role radio) + one `PRM_CredTile_Config__mdt` record mapped to `PRM_SpecialtyVerification__c`.
Out of scope: the board; the controller; the address action center's taxonomy internals (may reference existing pickers by reuse).

## Acceptance Criteria

Scenario 1 - CAQH specialty renders read-only beside editable SF taxonomy
Given a practitioner with CAQH specialties and SF `HealthcareProviderTaxonomy` records
When the specialist opens the Taxonomy tile
Then CAQH specialties render read-only and SF taxonomy records render editable

Scenario 2 - Add and remove SF taxonomy
Given the Taxonomy tile is open
When the specialist adds and removes a taxonomy record and saves
Then the SF taxonomy records are updated and no CAQH data is modified

Scenario 3 - Practitioner Role selection persists
Given the specialist selects PCP / Specialist / Dual
When they save
Then the role is persisted

Scenario 4 - Status derives from PRM_SpecialtyVerification__c
Given `PRM_SpecialtyVerification__c` = 'Data Looks Good'
When the board derives status
Then the Taxonomy tile shows Completed

## Technical Section
- Reuse existing multi-select pickers (`prmMultiSelectPicklist`/`prmCheckboxList`) by reference; reuse selectors for taxonomy reads.
- Record: taxonomy -> `PRM_SpecialtyVerification__c` (required), `PRM_TileComponent__c` = `prmCredTileTaxonomy`, `PRM_LaunchTarget__c` blank, available.
- One bulk DML for taxonomy save; WITH USER_MODE.

## Impact Analysis
- Net-new LWC (own bundle) + own CMDT record — parallel-safe.
- May reuse `PRM_SpecialtyPSV__c` as a secondary signal — confirm.

## Clarification Questions
- Confirm the SF taxonomy object/fields and whether an existing controller saves them (avoid a new class) — [VERIFY].
- Confirm Practitioner Role field API name and picklist values — [VERIFY].

## Estimated Effort
_AI-estimated — validate with team._

| Component | Effort | Notes |
|-----------|--------|-------|
| `prmCredTileTaxonomy` + Jest | 1.5d | CAQH read-only + SF CRUD + role |
| CMDT record + wiring | 0.5d | mapping |
| **Total** | **2d** | Wave 1 |
