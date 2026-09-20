# CRED-13: Parity Validation, Shadow Run & Cutover/Rollback

> **Epic:** [Initial Credentialing Review — Tile Dashboard](EPIC_Initial_Cred_Review_Tile_Dashboard.md) · **Priority:** High · **Depends on:** CRED-2..CRED-12 · **Blocks:** GA

## Story
**Persona:** Credentialing Lead / QA Engineer

**As a** credentialing lead,
**I want** to validate the tile flow produces identical records to the legacy OmniScripts and cut over safely with a rollback,
**So that** we adopt the tile dashboard without regressing production credentialing.

## Scope
In scope: parity test suite (both branches + all submit outcomes), shadow-run plan on pilot cases, performance validation (esp. high-volume address), pilot gating via permission set, cutover (re-point entry) and rollback runbook.
Out of scope: building any tile/feature (delivered by CRED-1..CRED-12).

## Acceptance Criteria

Scenario 1 - Field-by-field parity for standard outcome
Given the same pilot case processed via the tile flow and the legacy OmniScript
When both submit with the standard approve outcome
Then resulting IndividualApplication/Case/child field values match

Scenario 2 - Parity for route-to-QC outcome
Given a pilot case
When submitted via the tile flow with "Route directly to QC"
Then `PRM_Stage__c` = 'QC Review' and the QC Case + queue ownership match the legacy PSV->QC path

Scenario 3 - Historical case renders with no backfill
Given a pre-existing case created before this feature
When opened in the tile board
Then all tile statuses derive correctly from existing fields with no data migration

Scenario 4 - Performance targets met
Given a case with 100+ addresses
When the board and address tile load
Then board load < 3s and the address tile paginates/loads without timeout

Scenario 5 - Pilot gating
Given a non-pilot user
When they open the Case Manager page
Then the board is not visible (permission-set gated)

Scenario 6 - Cutover and rollback
Given cutover re-points the entry to the tile board
When a regression is detected
Then re-pointing back to the OmniScript restores the legacy path with no data migration (same shared IP)

## Technical Section
- Parity harness: run fixtures through both paths; diff IA/Case/child records per outcome (Approve, Route-to-QC, Return-to-Outreach, Return-to-App-Review).
- Shadow run on a pilot reviewer group (permission set + App Builder visibility) for ~2 weeks.
- Perf: board load, tile save, resume; 100+ address volume.
- Cutover: re-point the launch/remote action from the OmniScript to the board. Rollback: re-point back (IP unchanged/shared).

## Impact Analysis
- No new components; validates and switches the entry point.
- Gates GA; last story in the epic.

## Clarification Questions
- Confirm pilot reviewer group + duration — [VERIFY].
- Confirm the entry point being re-pointed (launch button / remote action / record-page component) — [VERIFY].
- Confirm SLO thresholds for sign-off (design §3.3 / §11) — [VERIFY].

## Estimated Effort
_AI-estimated — validate with team._

| Component | Effort | Notes |
|-----------|--------|-------|
| Parity harness + outcomes | 1.5d | 4 outcomes x 2 branches |
| Shadow-run + perf validation | 1d | pilot, 100+ addresses |
| Cutover + rollback runbook | 0.5d | re-point entry |
| **Total** | **3d** | Wave 3 |
