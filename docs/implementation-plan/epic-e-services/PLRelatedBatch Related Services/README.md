# PLRelatedBatch Related Services *(seq 4)*

> **Batch:** `PRM_PLRelatedBatch` — sequence‑4 of the async pipeline (`PRM_AsyncOrchestrator`, halt‑on‑failure). Runs **after** `PracticeLocationAndGroupBatch` (seq 2) has created the location/facility graph; builds the **practice‑location‑related** records (affiliations, features, networks).
> **Parent guide:** `Epic_E_Practitioner_Services_Part3.md`. **Sibling batch designs:** `E20_PRM_PractitionerBatch.md` (seq 1) · `E21_PRM_PracticeLocationAndGroupBatch.md` (seq 2).

## Services this batch orchestrates (Part 3)

| E# | Service | Writes | Notes |
|---|---|---|---|
| **E14** | `PRM_HPFService` (+ `PractionerPracticeLocationService` sub‑service) | `HealthcarePractitionerFacility` | practitioner ↔ location affiliation |
| **E15** | `PRM_ProviderFeatureService` | `PRM_ProviderFeature__c` | assistive aids + affirming care categories |
| ~~E17~~ | ~~`PRM_HealthcareFacilityNetworkService`~~ | ~~`HealthcareFacilityNetwork`~~ | **DROPPED** — the facility-grain `PRM_FacilityNw`+`PRM_FacilityTx` are auto‑created by the **`PRM_HealthcareFacilityNetworkTrigger`** when E18 inserts the Level‑4 `HealthcareFacilityNetwork` rows (RT `PRM_FacilityPractitionerTxNw`); owned by the **Level‑4 flow (E18)**, not this batch |

## Planned files (to be added, mirroring E03/E13/E20/E21)

- `E14_PRM_HPFService.md` ✅ (+ `_Execution_Plan.md` pending)
- `E15_PRM_ProviderFeatureService.md` ✅ (+ `_Execution_Plan.md` pending)
- ~~`E17_PRM_HealthcareFacilityNetworkService.md`~~ — **DROPPED** (HFN trigger‑created in E18/Level‑4; see E22 §10 OQ‑E22‑3)
- `E22_PRM_PLRelatedBatch.md` ✅ — the batch design (orchestration + CMA/CDM wiring, like E20/E21)

> **✅ CMA/CDM applicability (org‑verified):** both apply to E14 + E15 and are **emitted by `E22` (not triggers)** — E14 → CMA `Practitioner_Practice_Location` + CDM `HealthCarePractitionerFacility`; E15 → CMA `Provider_Feature` + CDM `ProviderFeature`. See `E22_PRM_PLRelatedBatch.md` §9.

> **Cross‑batch note (CL‑E2‑13):** E13 (seq 2) was historically documented as invoking E14/E15 in‑process; the ratified model places **E14/E15 here in `PLRelatedBatch` (seq 4)** — E13 defers to this batch (see `E13_PRM_HealthcareFacilityCreationService.md` OQ‑E13‑3). **E17 is dropped** — HFN is a trigger side‑effect of E18/Level‑4.
> **Source:** `location.networkTaxonomyRoles[]` (network/taxonomy/role) + `location.capabilitiesAtLocation` (features) in `docs/sampleInputs/PractitionerCreation/PRM_MultiPractitioner_lowvolume.json`.
