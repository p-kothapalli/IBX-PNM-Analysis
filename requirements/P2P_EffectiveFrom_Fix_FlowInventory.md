# HCPF Update Inventory — Which Flows Touch P2P Records

> **Purpose**: Definitive list of every code path that writes to `HealthcarePractitionerFacility` (HCPF), with the subset that touches **P2P record-type** (`PRM_PractitionerPracticeAffiliation`) rows called out separately.
>
> Built to answer: *"Out of all the flows that update HCPF, which ones update P2P records, and which guided flows do they belong to?"*
>
> **Bottom line up front**: **9 guided flows actively write to P2P today.** All 9 go through standard Salesforce DML and will flow through the new helper without any modification. See [`P2P_EffectiveFrom_Fix_DevStory.md` §2A](./P2P_EffectiveFrom_Fix_DevStory.md#2a-scope-verification--why-a-trigger-only-fix-is-sufficient-no-drip-changes-required) for the scope-verification audit.
>
> **Per-flow `EffectiveTo` + bad-date scenarios** (back-date / future-date / range-mismatch overrides for every flow in §3) → [`P2P_EffectiveTo_Override_Scenarios.md`](./P2P_EffectiveTo_Override_Scenarios.md).

---

## 1. The 3 Record Types on `HealthcarePractitionerFacility`

| Record Type Dev Name | Common Name | `HealthcareFacilityId` | Unique key | `PRM_GlobalConstant` |
|---|---|---|---|---|
| `PRM_PractitionerLocationAffiliation` | **PPL** (Practitioner Practice Location) | Required | `(AccountId, HealthcareFacilityId, PractitionerId)` | `RECTYPEID_PLAFFILIATION` |
| `PRM_PractitionerPracticeAffiliation` | **P2P** (Practice to Practitioner) | **NULL** | `(AccountId, PractitionerId)` | `RECTYPEID_PRACTITIONERPL` |
| `PRM_AdmittingPrivileges` | **AP** (Admitting Privileges) | Required | `(PractitionerId, HealthcareFacilityId)` | `RECTYPEID_ADMITTINGPRIVILEGES` |

QA volumes (live): 563K PPL + 230K P2P + 268K AP.

---

## 2. Layer-by-Layer Inventory of HCPF Writers

### 2.1 Apex layer (33 classes)

Sorted into the 3 functional buckets below. **(P2P)** marker = class directly writes to P2P record type. **(PPL)** = writes PPL only. **(AP)** = writes Admitting Privileges. **(*)** = writes all three, depending on path.

#### Creation / activation paths

| Class | Records written | Triggered by |
|---|---|---|
| `PRM_AddNewLocationUtilityHelper` | PPL + **(P2P)** | Add Practitioner / Link PL OmniScripts |
| `PRM_PracLocNetworkAutomationService` | PPL | Practice Location creation |
| `PRM_PracticeLocationAutomationService` | PPL | Practice Location automation batch |
| `PRM_HcFacilityNetworkAutomationBatch` | PPL | Async network automation |
| `PRM_PractitionerActivationBatch` + `Helper` | * | Practitioner activation flow |
| `DFX_PractitionerActivationExecutor` | * | Data-fix executor |
| `PRM_AccountTermInitalCredService` | * | Account/Practitioner initial-cred flow |

#### Termination paths

| Class | Records written | Triggered by |
|---|---|---|
| `PRM_PracticeLocationTerminationBatch` + `PRM_PracLocTermHelper` | PPL + AP | **Practice Location Termination** guided flow |
| `PRM_AccountTerminationBatch` + `Helper` | PPL + AP + **(P2P)** | **Account Termination** guided flow |
| `PRM_PractitionerTerminationBatch` + `Helper` | PPL + AP + **(P2P)** | **Practitioner Termination** guided flow |
| `PRM_PractitionerTermForFacilityBatch` | PPL + AP + **(P2P)** | Chained from PL Term to per-practitioner term |
| `PRM_PractitionerTermRelateToVendorBatch` | PPL + **(P2P)** | Vendor relationship termination |
| `PRM_FullPractitionerTerminationBatch` | PPL + AP + **(P2P)** | Full pract term (during recred) |
| `PRM_FullPracTermRecredBatchService` | PPL + AP + **(P2P)** | Full pract term recred |
| `PRM_PractitionerTermInitalCredService` | * | Pract term during initial cred |
| `PRM_ProvChangeTerminationBatch` + `PRM_ProviderChangePracLocTermUtil` | PPL + **(P2P)** | **Provider Change** guided flow |
| `PRM_ManualUpdatePracLocTerminationBatch` | PPL | **PDM Manual Updates** for PL term |
| `PRM_PracLocTerminationUtilityPDM` + `PRM_PracLocTermPDMService` | PPL | PDM cross-ref termination |
| `PRM_RCATLocationTerminationBatch` + `PRM_RCATTerminationBatchHelper` + `PRM_RCATTerminationEffectivityHelper` | PPL + AP | RCAT (Re-Credentialing Action Tracking) term |
| `PRM_PDMUnlinkPractitioner` | PPL + **(P2P)** | **Unlink PL from Practitioner** guided flow |
| `DFX_TermPracLocRelatedRecExecutor` | PPL | Data-fix executor |

#### Cross-reference / PDM / reinstate paths

| Class | Records written | Triggered by |
|---|---|---|
| `PRM_CrossRefBatch` + `PRM_CrossRefBatchHelper` | PPL + **(P2P)** | **Account Creation Cross-Reference** guided flow |
| `PRM_CrossReferencePracticeLocation` | PPL + **(P2P)** *(only when ALL PPLs for pair terminate)* | Cross-reference cascade |
| `PRM_ManualUpdatesCrossRefBatchHelper` | PPL + **(P2P)** | **Manual Updates QC** guided flow |
| `PRM_ReinstateUtils` | PPL + AP + **(P2P)** | **Practice Location Reinstate**, **Practitioner Reinstate** guided flows |
| `PRM_ReinstateVendorAccountBatchHelper` *(invoked via PRM_ReinstateVendorAccountBatch)* | PPL + AP + **(P2P)** | **Account Reinstate** guided flow |
| `PRM_PDMDataHelper` | * | PDM helper |
| `PRM_OffCycleWrapper` + `PRM_CheckCAQHDataHelper` | * | Off-Cycle flows |

#### Trigger handler & support utilities

| Class | Records written | Notes |
|---|---|---|
| `PRM_PracFacilityTriggerHandler` | * | The trigger handler (does not initiate DML; reacts to it) |
| `PRM_HCPFTriggerHelper` | * (P2P only after this fix ships) | Same — and the helper this story adds |
| `PRM_ConciergeRollupHelper` + `PRM_ConciergeProviderRollupQueueable` | PPL | Concierge rollup recalc |
| `PRM_PNCPDAService` + `PRM_PNCPDABatchHelper` | PPL | PNC PDA processing |
| `PRM_CaseManagerAssociationBatch` | PPL | Case manager re-assignment |
| `PRM_LetterRecredBatch` + `PRM_LetterWelcomeBatch` | * (reads + status updates) | Async letter generation |
| `PRM_AdverseActionLogService` | * | Adverse-action logging |
| `PRM_UpdateDeniedFacilityAddress` | * | Denied-facility cleanup |
| `DFX_PractitionerPrimaryLocationExecutor` + `PRM_PractitionerPrimaryLocationExecutor` | PPL | Primary location data-fix |
| `DFX_RevertEffectiveFromDateExecutor` | * | EffectiveFrom rollback data-fix |
| `PRM_OmniProcessUtilsHelper` | * | Wraps the Future-Dated Processing batch |

### 2.2 DataRaptor layer (74 DRs target HCPF)

Sorted by **what record type they write** and **whether the EffectiveFrom mapping is enabled**.

#### DRs that write to P2P (RecordType = `PRM_PractitionerPracticeAffiliation`)

| DataRaptor | Action | EffectiveFrom mapping | Used by |
|---|---|---|---|
| `PRMDRCreateHCPFForPractitionerPracAffiliation_1` | INSERT | **ACTIVE** (line 135) | Account Creation Cross-Ref, Practitioner Creation, Add Practitioner |
| `PRMDRCreateHCPFForPractitionerPracAffiliationDelg_1` | INSERT | ACTIVE | Delegated Practitioner Creation |
| `PRMDRCreatePPLForPPA_1` | INSERT | **DISABLED** (line 101) | Same family — no-op for EffectiveFrom today |
| `PRMDRCreatePPLForPPADelg_1` | INSERT | DISABLED | Same family — Delg variant |
| `PRMUpdatePracticeToPractitioner_1` | UPDATE | **DISABLED** (line 115) | PDM Manual Updates (the most-misleadingly-named DR — looks like a P2P writer, but EffectiveFrom output is off) |
| `PRMUpdatePracticeToPractitionerDelg_1` | UPDATE | **ACTIVE** (line 104) | Delegated PDM Manual Updates |
| `DRToUpdatePracToPracitionerafterReInstate_1` | UPDATE | Updates IsActive (not EffectiveFrom directly) | Reinstate flows |
| `PRMReinstatehealthcareFacilityUpdate_1` | UPDATE | Updates IsActive + EffectiveTo | Reinstate flows |
| `PRMLoadReinstatePractPracLoc_1` | LOAD/UPSERT | Indirect | Reinstate flows |
| `PRMDRPPractionerPracticeLocations_1` | UPSERT | Indirect | Practitioner data update |
| `PRMDRLoadPracticeToPracLocation_1` | LOAD/UPSERT | Indirect | Cross-reference loads |
| `PRMDRUPracLocNetPracticeToPractitoner_1` | UPDATE | Indirect | PL Network ↔ P2P sync |
| `PRMDRPDelegatedPractionerPracticeLocations_1` | UPSERT | Indirect | Delegated practitioner flow |
| `PRMDRLoadUpdatePPL_1` | UPDATE | Indirect | Generic PPL/P2P update path |

#### DRs that write PPL only (the trigger uses these as INPUT — keep as-is)

15 DRs in this category. Examples: `PRMDRCreatePractitionerNewAddressRecords_1`, `PRMDRPHCPractFacHCFacilityLocationAddress_1`, `PRMDRCreatePractitionerAddAddressRecords_1`, `PRMLoadPDMPracFacilities_1`, `PRMLoadPPLPDM_1`, `PRMLoadPractitionerFacilities_1`, etc. (full list in the impact analysis).

#### DRs that write Admitting Privileges or generic HCPF (don't affect P2P EffectiveFrom)

40+ DRs in this category. Examples: `PRMCreateHCPFForAdmittingPriviliges_1`, `PRMDRPUpsertAdmPrivilidges_1`, all the `*PCFPDA*`, `*PDAReview*`, `*RCAT*`, `*NonPar*` DRs. Their writes target other record types or unrelated fields.

### 2.3 Integration Procedure layer

IPs **do not DML directly** — they invoke DataRaptors. So an IP "writes" to HCPF only because it calls one of the DRs above. No IP needs to change for the fix.

The IPs that compose multiple HCPF-touching DRs (informational, since they're the orchestration layer for the guided flows):

| Integration Procedure | What it orchestrates | Touches P2P? |
|---|---|---|
| `PRM_CrossReferencePDMManualUpdate_Procedure_*` | Account creation cross-reference | **Yes** (via `PRMDRCreateHCPFForPractitionerPracAffiliation_1`) |
| `PRM_PDMLinkPracticeLocationHelper_Procedure_*` | PDM Link PL | Yes (creates P2P if missing) |
| `PRM_PDMLinkUnlinkPracticeLocationHelper_Procedure_*` | PDM Link/Unlink PL | Yes (clears P2P EffectiveTo on relink) |
| `PRM_PDMRecordsCreationPracLocation_Procedure_*` | PDM PL creation | Yes |
| `PRM_PDMRecordsCreationHelper_Procedure_*` | PDM record creation | Yes |
| `PRM_PDMRecordsPractitionerCreationHelper_Procedure_*` | PDM Practitioner creation | Yes |
| `PRM_CreateRecordsForPCF_Procedure_*` | PCF (Practitioner Case File) creation | Yes |
| `PRM_OffCycleRecordCreation_Procedure_*` | Off-Cycle record creation | Yes (off-cycle credentialing creates P2P) |
| `PRM_ReinstateRecordCreation_Procedure_*` + `_Parent_*` | Reinstate flows | Yes |
| `PRM_PracticeLocationTermination_Procedure_*` | PL Termination orchestrator | **Yes** via `PRM_CrossReferencePracticeLocation` Apex |
| `PRM_PractitionerTerminationRecordsUpdate_Procedure_*` | Pract Termination orchestrator | Yes |
| `PRM_ReinstatePracticeLocation_Procedure_*` | PL Reinstate | Yes |
| `PRM_NonParRecordCreations_Procedure_*` | Non-Par enrollment | Yes |
| `PRM_AccountTypeRecordCreations_Procedure_*` | Account creation orchestrator | Yes |
| `PRM_ContractHierarchyCreations_Procedure_*` | Contract hierarchy | Yes |
| `PRM_DelegatedPractitionerCreation_Procedure_*` + `PRM_CreateDelegatedPractitionerPracticeLocationsRecords_Procedure_*` | Delegated pract creation | Yes |
| `PRM_ProviderChangePDAUpdates_Procedure_*` | Provider Change PDA | Yes |
| `PRM_NonroutineCommitteeReviewUpdate_Procedure_*` | Non-routine committee | No (touches HCPF status only) |

### 2.4 OmniScript / Guided Flow layer

This is the user-facing layer. Below is the **full map** of which guided flows touch HCPF, and which subset touches P2P.

---

## 3. The Headline Table — Guided Flows That Update P2P

| # | Guided Flow (OmniScript) | Updates HCPF | **Updates P2P?** | Primary mechanism | Section in impact analysis |
|---|---|---|---|---|---|
| 1 | **Account Creation Cross-Reference** (`PRM_AccountCreation_English_*`) | ✓ | **YES — INSERT P2P** | `PRMDRCreateHCPFForPractitionerPracAffiliation_1` + `PRM_CrossRefBatch` | §5 Scenario 1 |
| 2 | **PDM Manual Updates — Practitioner / Group / PL** (`PRM_PDMManualUpdate_*`, `PRM_PDMManualChanges_*`, `PRM_PDMManualUpdatePractitioner_*`, `PRM_PDMManualUpdatePracticeLocation_*`, `PRM_PDMManualUpdateVendorAccount_*`, `PRM_PDMManualUpdateHCFAssociations_*`) | ✓ | **YES — UPDATE P2P** | `PRMUpdatePracticeToPractitionerDelg_1` (Delg variant) + `PRM_ManualUpdatesCrossRefBatchHelper` |
| 3 | **Unlink Practice Location from Practitioner** | ✓ | **YES — UPDATE P2P EffectiveTo** | `PRM_PDMUnlinkPractitioner` Apex |
| 4 | **Link Practice Location from Practitioner** (via PDM Manual Update) | ✓ | **YES — INSERT P2P or UPDATE EffectiveTo→null** | `PRM_PDMLinkPracticeLocationHelper_Procedure_*` IPs + `PRM_AddNewLocationUtilityHelper` |
| 5 | **Add Practitioner to Practice Location** (`PRM_PractitionerCreation_*`) | ✓ | **YES — INSERT P2P** | `PRM_AddNewLocationUtilityHelper` + creation DRs |
| 6 | **Practice Location Termination** (`PRM_PracticeLocationTermination_English_*`) | ✓ | **YES — UPDATE P2P EffectiveTo (when ALL PPLs for pair are terming)** | `PRM_PracticeLocationTerminationBatch` → `PRM_CrossReferencePracticeLocation` → P2P EffectiveTo |
| 7 | **Account Termination** (`PRM_AccountTerminationForm_English_*`) | ✓ | **YES — UPDATE P2P EffectiveTo** | `PRM_AccountTerminationBatch` + Helper |
| 8 | **Practitioner Termination** (`PRM_PractitionerTerminationForm_*`, `PRM_PractitionerTerminationRecredForm_*`) | ✓ | **YES — UPDATE P2P EffectiveTo** | `PRM_PractitionerTerminationBatch` + Helper, `PRM_FullPractitionerTerminationBatch`, `PRM_PractitionerTermRelateToVendorBatch` |
| 9 | **Provider Change Request** (`PRM_ProviderChangeForm_*`, `PRM_ProviderChangePDAUpdate_*`, `PRM_ProviderChangeQC_*`) | ✓ | **YES — UPDATE P2P EffectiveTo** | `PRM_ProvChangeTerminationBatch` + `PRM_ProviderChangePracLocTermUtil` |
| 10 | **Practice Location Reinstate** (`PRM_PracticeLocationReinstate_English_*`) | ✓ | **YES — UPDATE P2P (clears EffectiveTo, sets IsActive=true)** | `PRM_ReinstateUtils` + reinstate DRs |
| 11 | **Practitioner Reinstate** (`PRM_PractitionerReinstateForm_English_*`, `PRM_ReinstateLinkExistingPractitioner_English_*`) | ✓ | **YES — UPDATE P2P** | `PRM_ReinstateUtils` |
| 12 | **Account Reinstate** (`PRM_PractitionerReinstateVendorForm_English_*`) | ✓ | **YES — UPDATE P2P (writes EffectiveFrom directly today — Phase 2 cleanup)** | `PRM_ReinstateVendorAccountBatchHelper` lines 327-335 |
| 13 | **Manual Updates QC** (`PRM_ManualUpdatesQC_English_*`) | ✓ | **YES — INSERT P2P** at creation | `PRM_ManualUpdatesCrossRefBatchHelper` line 175 |
| 14 | **Off-Cycle Verification / PDA Review / QC Review** (`PRM_OffCycleVerification_*`, `PRM_OffCyclePDAReview_*`, `PRM_OffCycleQCReview_*`) | ✓ | Possibly — depends on off-cycle action | `PRM_OffCycleWrapper` + `PRM_OffCycleRecordCreation_Procedure_*` IPs |
| 15 | **Delegated Practitioner Creation** (used inside PDM flows) | ✓ | **YES — INSERT P2P (Delg variant)** | `PRMDRCreateHCPFForPractitionerPracAffiliationDelg_1` + `PRMUpdatePracticeToPractitionerDelg_1` |
| 16 | **Non-Par Provider Enrollment** (`PRM_NonParReview_*`, `PRM_NonParQCReview_*`) | ✓ | **YES — INSERT P2P at non-par enrollment** | `PRM_NonParRecordCreations_Procedure_*` IPs |
| 17 | **Practice Location Bundles** (`PRM_PracticeLocationBundles_*`) | ✓ | No — touches HCPF for bundle associations only | `PRMUpdateHcPractiFacLocationBundleAsso_1` |
| 18 | **Update Primary Practice Location** (`PRM_UpdatePrimaryPracticeLocation_*`) | ✓ | No — updates `IsPrimary` flag on PPL | PPL-only |
| 19 | **Practice Location Creation / Cross-Reference** (`PRM_AccountCreation_*` sub-paths) | ✓ | Yes when PPA is being established | Same family as #1 |
| 20 | **Supplier Network Creation** (`PRM_SupplierNetworkCreation_*`) | ✓ | No — Account contract hierarchy only | N/A |
| 21 | **Attestation Flow** (`PRM_AttestationFlow_English_*`) | ✓ | No — updates Attestation date on PPL only | `PRMDRUAttestationDatePractitionerPracLoc_1`, `PRMDRUpdateAttestationDate_1` |
| 22 | **PSV Review / Ancillary Reassessment** (`PRM_PrimarySourceVerificationReview_*`, `PRM_PSVSubOsSummary_*`, `PRM_AncillaryReassessmentPSV_*`) | ✓ | No — updates PSV-related fields only | N/A |
| 23 | **Contract Hierarchy** (`PRM_ContractHierarchy_*`) | ✓ | No — Account contracts only | N/A |
| 24 | **Update Board Certification** (`PRM_UpdateBoardCertification_*`) | No (touches Board Cert object) | No | N/A |

**Tally**: 16 guided flows in the user's original list, plus 8 adjacent flows discovered during the audit. **9 of them actively WRITE to P2P records today** — those are rows 1-9 in the table above. Three more (rows 12, 13, 15) write P2P at insert time which is correct by construction. Rows 16-24 do not write P2P EffectiveFrom and are unaffected by this work.

---

## 4. Background / Async Paths (not user-initiated, but still update HCPF)

| Batch / Async path | Touches P2P? | Notes |
|---|---|---|
| `PRM_FutureDatedProcessingBatch` (nightly) | **Yes** (indirectly) | Flips `IsActive` on PPL when `EffectiveFrom/To` arrives → triggers our helper → P2P EffectiveFrom recomputes |
| `PRM_PractitionerActivationBatch` | Yes | Activates HCPF records when EffectiveFrom hits |
| `PRM_LetterRecredBatch`, `PRM_LetterWelcomeBatch` | No | Read HCPF for letter generation, don't write |
| `PRM_HcFacilityNetworkAutomationBatch` | No | HFN automation; PPL only |
| `PRM_RCATNetworkTerminationBatch` | No directly | RCAT terminations target HFN |
| `PRM_RCATLocationTerminationBatch` | Yes | RCAT-driven PL termination cascades to P2P |
| `PRM_PracticeLocationAutomationBatch` | No | Creates PPL only |
| `PRM_NetworkCreationBatch` | No | Creates HFN |
| `PRM_UpdateHCFNetworkBatch` | No | HFN |
| `PRM_HFNCascadeBatch` | No | HFN cascade |
| `PRM_BCBSAGenerateOrgAffiliation` + `PRM_BCBSARecordSyncSubServiceHandler` | No | BCBSA org affiliations |
| `PRM_CaseManagerAssociationBatch` | No | CM associations |
| Data-fix DFX executors (10+ classes) | Varies | One-off data fixes — some touch P2P, all run through the trigger |

---

## 5. Net Conclusion

**Total HCPF writer count**: 33 Apex classes + 74 DataRaptors + ~130 IPs that orchestrate them + 24 guided flows.

**Subset that writes P2P records today**: 18 Apex classes + 14 DataRaptors + ~25 IPs + **9 user-initiated guided flows** (rows 1-9 in §3) + 3 P2P-create-at-construction-time flows (rows 12-13, 15) + 2 background async paths.

**All of them funnel through Salesforce DML on `HealthcarePractitionerFacility`**, which means all of them trigger our helper. **Zero need to modify any of them for the fix to work.**

The only two Apex writes that produce a "transient incorrect value the trigger overwrites" are:

1. `PRM_ReinstateVendorAccountBatchHelper.cls` lines 327-335 — explicitly assigns `obj.EffectiveFrom = inputEffectiveFrom` on P2P during Account Reinstate
2. `PRMUpdatePracticeToPractitionerDelg_1` DataRaptor — actively writes P2P `EffectiveFrom` from input `EffectiveDate` during Delegated PDM Manual Updates

Those two are the **Phase 2 cleanup targets** in the impact analysis — purely cosmetic, both work correctly today because the trigger overwrites them within the same transaction.
