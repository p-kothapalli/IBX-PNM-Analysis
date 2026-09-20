# Level4RecordCreationBatch Related Services *(seq 5)*

> **Batch:** `PRM_Level4Batch` — sequence‑5 (final) of the async pipeline (`PRM_AsyncOrchestrator`, halt‑on‑failure). Runs **after** `PLRelatedBatch` (seq 4); creates the **Level‑4** records that depend on the full location/affiliation graph.
> **Parent guide:** `Epic_E_Practitioner_Services_Part3.md`. **Sibling batch designs:** `E20_PRM_PractitionerBatch.md` (seq 1) · `E21_PRM_PracticeLocationAndGroupBatch.md` (seq 2).

## Services this batch orchestrates (Part 3)

| E# | Service | Writes | Notes |
|---|---|---|---|
| **E18** | `PRM_Level4RecordCreationService` ✅ | `HealthcareFacilityNetwork` · RT **`PRM_FacilityPractitionerTxNw`** (Level‑4) | one per (practitioner × location × network × taxonomy × role), from `location.networkTaxonomyRoles[]` |

> **⚡ Trigger cascade (org‑verified):** on E18's TxNw insert, `PRM_HealthcareFacilityNetworkTrigger` → `PRM_HCFacilityNetworkTriggerHelper` auto‑creates the **`PRM_FacilityNw` (Practice Location Network)** + **`PRM_FacilityTx` (Practice Location Taxonomy)** rows (deduped) and sets *their* `SourceSystemIdentifier`. So the former **E17 is a trigger side‑effect** — E18 creates **only** the TxNw. E18/E23 run with **bulk‑context OFF** so the trigger fires (`BatchSize=1`).

## Files

- `E18_PRM_Level4RecordCreationService.md` ✅ (+ `_Execution_Plan.md` pending)
- `E23_PRM_Level4Batch.md` ✅ — the batch design (orchestration, seq 5; class `PRM_Level4Batch`)

## Decisions (2026‑07)

- **New** service + batch (not reusing the legacy `PRM_NetworkCreationBatch`/`PRM_NetworkCreationHelper`).
- **Idempotency:** Unique `SourceSystemIdentifier = {practitionerId}_{healthcareFacilityId}_{payerNetworkId}_{careTaxonomyCode}_{role}` (set by E18; pre‑check + insert‑misses; not `upsert` — field is Unique but not an External Id).
- **Reference Ids resolved by E23** (SOQL‑free E18): HCF via shared `PRM_FormSubUtility.computeHcfExternalId`; `HealthcarePayerNetwork` by `Name` (exact); `CareTaxonomy` by code; `isPrimarySpecialty` from `practitioner.taxonomies[]`.
- **No CMA, no CDM, no IFC loader** for this batch (for now).
- `PRM_PractitionerRole__c` ∈ {`PCP`,`Specialist`}; `PRM_Taxonomy__c` → `CareTaxonomy`; `PayerNetworkId` → `HealthcarePayerNetwork`.
