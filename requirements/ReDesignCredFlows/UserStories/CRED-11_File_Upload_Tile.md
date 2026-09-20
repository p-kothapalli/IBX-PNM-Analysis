# CRED-11: File Upload Tile (reuse document viewer + thin upload)

> **Epic:** [Initial Credentialing Review — Tile Dashboard](EPIC_Initial_Cred_Review_Tile_Dashboard.md) · **Priority:** Low · **Depends on:** CRED-1 · **Parallel with:** all other Wave-1 tiles

## Story
**Persona:** Credentialing Specialist (reviewer)

**As a** credentialing specialist,
**I want** a File Upload tile to view existing documents and upload attachments for the case,
**So that** I can manage supporting files from the dashboard.

## Scope
In scope: net-new thin LWC `prmCredTileFileUpload` that reuses `prmContentDocumentViewer`/`prmViewFileFromSDS` for viewing and `lightning-file-upload` for uploads, linked to the Case Manager; one `PRM_CredTile_Config__mdt` record.
Out of scope: the board; the controller; document management backend changes.

## Acceptance Criteria

Scenario 1 - Existing documents render
Given the Case Manager has linked ContentDocuments
When the specialist opens the File Upload tile
Then existing documents render via the reused viewer

Scenario 2 - Upload attaches to the Case Manager
Given the specialist uploads a file
When the upload completes
Then a ContentDocumentLink is created against the Case Manager

Scenario 3 - Status derives from document presence
Given at least one document is linked
When the board derives status
Then the File Upload tile shows Completed (else Pending)

## Technical Section
- Reuse `prmContentDocumentViewer` / `prmViewFileFromSDS` by reference; `lightning-file-upload` with `recordId` = Case Manager.
- Record: fileUpload -> blank `PRM_SourceField__c` (derive by ContentDocumentLink presence), `PRM_TileComponent__c` = `prmCredTileFileUpload`, optional, available.

## Impact Analysis
- Net-new thin LWC (own bundle) + own CMDT record — parallel-safe.

## Clarification Questions
- Confirm the document linkage pattern (ContentDocumentLink to IA vs. an SDS pattern) — [VERIFY].

## Estimated Effort
_AI-estimated — validate with team._

| Component | Effort | Notes |
|-----------|--------|-------|
| `prmCredTileFileUpload` + Jest | 0.75d | view + upload |
| CMDT record | 0.25d | mapping |
| **Total** | **1d** | Wave 1 |
