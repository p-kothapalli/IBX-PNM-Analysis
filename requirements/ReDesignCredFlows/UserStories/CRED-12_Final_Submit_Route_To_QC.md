# CRED-12: Final Submit + Route-Directly-to-QC

> **Epic:** [Initial Credentialing Review — Tile Dashboard](EPIC_Initial_Cred_Review_Tile_Dashboard.md) · **Priority:** Critical · **Depends on:** CRED-1, CRED-2 · **Parallel with:** the tile stories

## Story
**Persona:** Credentialing Specialist (reviewer)

**As a** credentialing specialist who has completed the combined App Review + PSV,
**I want** a Final Submit step where I can choose an outcome — including "Route directly to QC" —
**So that** I can finish everything in one sitting and hand the case straight to the QC queue without an intermediate handoff, without breaking the existing routing.

## Scope
In scope: net-new `prmCredFinalSubmit` LWC (tile summary, required-tile gate, outcome selector) + `PRM_VerificationReviewController.submitCredentialingReview(Id caseManagerId, String outcome)` which sets `PRM_PSVOutcome__c` and invokes the existing IP `PRM_ReviewPSVCaseRecordsUpdate` (v27); one `PRM_CredTile_Config__mdt` record (finalSubmit).
Out of scope: changes to the IP or DataRaptor `PRMTransformPSVSetValuesIASplit` (base cases reuse existing values); QC flow build (separate epic); DataRaptor branch for a distinct "Direct to QC" value (only if D-1 chosen).

## Acceptance Criteria

Scenario 1 - Submit blocked until required tiles complete
Given one or more required tiles are not Completed
When the specialist opens Final Submit
Then the outcome selector is disabled and the incomplete required tiles are listed

Scenario 2 - Route directly to QC sets stage to QC Review
Given all required tiles are Completed
And the specialist selects "Route directly to QC"
When they submit
Then `PRM_PSVOutcome__c` is set to 'PSV QC' and the IP resolves `PRM_Stage__c` = 'QC Review' with `Status` = 'In Progress'

Scenario 3 - Handoff preserves segregation of duties
Given a case routed directly to QC
When submit completes
Then the QC Case is owned by the QC queue and the submitting specialist is not auto-advanced into QC tiles

Scenario 4 - Return to App Review outcome
Given the specialist selects "Return to App Review"
When they submit
Then `PRM_PSVOutcome__c` = 'Return to App Review' and the IP resolves `PRM_Stage__c` = 'Application Review'

Scenario 5 - Return to Outreach outcome
Given the specialist selects "Return to Outreach"
When they submit
Then `PRM_PSVOutcome__c` = 'Provider Outreach Needed' and the case routes to the outreach/PSV stage per the IP

Scenario 6 - Parity with the OmniScript submit
Given the same case data
When submitted via the tile flow vs the legacy OmniScript summary
Then the resulting IndividualApplication/Case field values match for each outcome

Scenario 7 - Submit is transactional and errors surface
Given the IP call fails
When the specialist submits
Then no partial routing is left and a clear error is shown

## Technical Section
- `submitCredentialingReview`: validate required verification fields (from CMDT `PRM_Required__c`) are in a completed value; set `PRM_PSVOutcome__c`; build the IP payload matching the OmniScript summary contract and invoke `PRM_ReviewPSVCaseRecordsUpdate` (via `omnistudio.IntegrationProcedureService` / callable, or the existing wrapper) `WITH USER_MODE`.
- Outcome -> `PRM_PSVOutcome__c` map: Approve/Proceed (existing approve value), Route directly to QC = `PSV QC`, Return to Outreach = `Provider Outreach Needed`, Return to App Review = `Return to App Review`.
- `prmCredFinalSubmit`: summary table from `getReviewState`, required-tile gate, outcome radio, confirm modal (`prmGenericConfirmModal`), notes.
- Record: finalSubmit -> `PRM_SourceField__c` = `PRM_PSVOutcome__c` (required), `PRM_TileComponent__c` = `prmCredFinalSubmit`, last sequence.

## Impact Analysis
- Uses the SAME IP the OmniScripts use — no existing flow breaks (design §7, §8).
- Adds one method to `PRM_VerificationReviewController` (owned here, not by tile stories) + one net-new LWC + one CMDT record.
- Downstream Committee/PDA OmniScripts unaffected.

## Clarification Questions
- Exact IP payload contract (outcome field + aggregated record structure) from a captured OmniScript submit — [VERIFY] (R1).
- The "Approve/Proceed" `PRM_PSVOutcome__c` value and its resulting stage — [VERIFY].
- D-1: distinguish "Direct to QC" from normal PSV->QC in reporting? If yes, add a distinct value + a one-line DataRaptor branch.

## Estimated Effort
_AI-estimated — validate with team._

| Component | Effort | Notes |
|-----------|--------|-------|
| `submitCredentialingReview` + tests | 1.5d | validation, IP invoke, parity |
| `prmCredFinalSubmit` + Jest | 1.25d | summary, gate, outcomes |
| CMDT record | 0.25d | mapping |
| **Total** | **3d** | Wave 2 |
