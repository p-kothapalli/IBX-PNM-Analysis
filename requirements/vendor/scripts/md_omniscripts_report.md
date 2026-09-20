# OmniScripts at risk: master-detail create/update failures

**Context:** A new release breaks Create / Update DML on objects that
are children of a master-detail relationship. The following OmniScripts
call (directly or transitively) an Integration Procedure that invokes a
DataRaptor Load writing to one of the MD-child objects below.

## Master-detail child objects in scope

| Child Object | Master-Detail Parent |
|---|---|
| `PRM_CaseManagerAssociation__c` | `IndividualApplication` |
| `PRM_ContactMethod__c` | `HealthcareFacility` |
| `PRM_ProgramParticipation__c` | `PRM_Program__c` |
| `PRM_CaseDataManager__c` | `IndividualApplication` |
| `PRM_AccountContractEntity__c` | `Account` |

**MD-writing DataRaptor Loads:** 52  
**Integration Procedures that (transitively) write to MD-child objects:** 87  
**Active+latest OmniScripts impacted:** 31

## Affected OmniScripts

Failure modes:
- **IP**: OmniScript calls an Integration Procedure that (transitively) writes to an MD-child object.
- **DR**: OmniScript has a `DataRaptor Post Action` step that writes directly to an MD-child object.

| # | OmniScript | Active | File | MD child object(s) written | Called IP(s) | Direct DR Load(s) |
|---|---|---|---|---|---|---|
| 1 | `AccountCreation_English` | Yes | `force-app/main/default/omniScripts/PRM_AccountCreation_English_31.os-meta.xml` | `PRM_AccountContractEntity__c`, `PRM_CaseDataManager__c` | PRM_AccountTypeCreationContainer | — |
| 2 | `AccountTerminationForm_English` | Yes | `force-app/main/default/omniScripts/PRM_AccountTerminationForm_English_9.os-meta.xml` | `PRM_CaseDataManager__c`, `PRM_ProgramParticipation__c` | PRM_AccountTerminationContainer | — |
| 3 | `AddAdditionalGroups_English` | Yes | `force-app/main/default/omniScripts/PRM_AddAdditionalGroups_English_7.os-meta.xml` | `PRM_CaseDataManager__c` | PRM_CreateAdditionalGroupsParent, PRM_ExistingPrimaryPracticeLocationLogic | — |
| 4 | `AddAncillaryPLAndBusinessLicense_English` | Yes | `force-app/main/default/omniScripts/PRM_AddAncillaryPLAndBusinessLicense_English_2.os-meta.xml` | `PRM_CaseManagerAssociation__c` | PRM_AncillaryAddPLAndLicenseCreationParent | — |
| 5 | `AncillaryPSVForm_English` | Yes | `force-app/main/default/omniScripts/PRM_AncillaryPSVForm_English_10.os-meta.xml` | `PRM_ContactMethod__c` | PRM_AncillaryPSVFormCreationParent | — |
| 6 | `AncillaryProviderForm_English` | Yes | `force-app/main/default/omniScripts/PRM_AncillaryProviderForm_English_38.os-meta.xml` | `PRM_CaseDataManager__c`, `PRM_CaseManagerAssociation__c` | PRM_AncillaryFormRecordsCreationParent | — |
| 7 | `AttestationFlow_English` | Yes | `force-app/main/default/omniScripts/PRM_AttestationFlow_English_19.os-meta.xml` | `PRM_ContactMethod__c` | PRM_UpdateAttestationDataParent | — |
| 8 | `ContractHierarchy_English` | Yes | `force-app/main/default/omniScripts/PRM_ContractHierarchy_English_7.os-meta.xml` | `PRM_AccountContractEntity__c`, `PRM_CaseDataManager__c` | PRM_ContractHierarchyCreationContainer | — |
| 9 | `Manage Practice Location Bundles_English` | Yes | `force-app/main/default/omniScripts/PRM_ManagePracticeLocationBundles_English_1.os-meta.xml` | `PRM_CaseDataManager__c` | PRM_ManageHCFBundleAssParents, PRM_PLBundleRecordCreationParent | — |
| 10 | `NonParProviderRegistration_English` | Yes | `force-app/main/default/omniScripts/PRM_NonParProviderRegistration_English_51.os-meta.xml` | `PRM_CaseDataManager__c` | PRM_NonParRecordCreationContainer | — |
| 11 | `PDMManualUpdateFHNaticPractitioner_English` | Yes | `force-app/main/default/omniScripts/PRM_PDMManualUpdateFHNaticPractitioner_English_2.os-meta.xml` | `PRM_CaseDataManager__c`, `PRM_ProgramParticipation__c` | PRM_PDMPractitionerRecordsCreationParent | — |
| 12 | `PDMManualUpdatePracticeLocation_English` | Yes | `force-app/main/default/omniScripts/PRM_PDMManualUpdatePracticeLocation_English_4.os-meta.xml` | `PRM_CaseDataManager__c`, `PRM_ProgramParticipation__c` | PRM_PDMRecordsCreationPracLocationParent | — |
| 13 | `PDMManualUpdateVendorAccount_English` | Yes | `force-app/main/default/omniScripts/PRM_PDMManualUpdateVendorAccount_English_2.os-meta.xml` | `PRM_CaseDataManager__c`, `PRM_ProgramParticipation__c` | PRM_PDMRecordsCreationForVendorAccountParent | — |
| 14 | `PDMManualUpdate_English` | Yes | `force-app/main/default/omniScripts/PRM_PDMManualUpdate_English_44.os-meta.xml` | `PRM_CaseDataManager__c`, `PRM_ProgramParticipation__c` | PRM_PDMRecordsCreationParent | — |
| 15 | `PRMNonParReview_English` | Yes | `force-app/main/default/omniScripts/PRM_NonParReview_English_25.os-meta.xml` | `PRM_ContactMethod__c` | PRM_ReviewRecordsUpdateParent | — |
| 16 | `PRMOffCycleVerification_English` | Yes | `force-app/main/default/omniScripts/PRM_OffCycleVerification_English_36.os-meta.xml` | `PRM_CaseDataManager__c` | PRM_OffCycleRecordCreationParent | — |
| 17 | `PRMPracticeLocationReinstate_English` | Yes | `force-app/main/default/omniScripts/PRM_PracticeLocationReinstate_English_6.os-meta.xml` | `PRM_CaseDataManager__c`, `PRM_ContactMethod__c`, `PRM_ProgramParticipation__c` | PRM_ReinstatePracticeLocationParent | — |
| 18 | `PRM_PDMManualChanges_English` | Yes | `force-app/main/default/omniScripts/PRM_PDMManualChanges_English_23.os-meta.xml` | `PRM_AccountContractEntity__c`, `PRM_ContactMethod__c`, `PRM_ProgramParticipation__c` | PRM_ManualChangePDAUpdateParent | — |
| 19 | `PSVSubOsTxnyRole_English` | Yes | `force-app/main/default/omniScripts/PRM_PSVSubOsTxnyRole_English_5.os-meta.xml` | `PRM_CaseDataManager__c` | PRM_ReviewPSVCaseRecordsUpdateParent | — |
| 20 | `PractitionerCreation_English` | Yes | `force-app/main/default/omniScripts/PRM_PractitionerCreation_English_21.os-meta.xml` | `PRM_CaseDataManager__c` | PRM_AddressLogicContainer, PRM_PractitionerCreationContainer | — |
| 21 | `PractitionerParticipationForm_English` | Yes | `force-app/main/default/omniScripts/PRM_PractitionerParticipationForm_English_111.os-meta.xml` | `PRM_CaseDataManager__c` | PRM_CreateParFormRecordsContainer, PRM_ExistingPrimaryPracticeLocationLogic | — |
| 22 | `PractitionerReinstateForm_English` | Yes | `force-app/main/default/omniScripts/PRM_PractitionerReinstateForm_English_9.os-meta.xml` | `PRM_CaseDataManager__c` | PRM_ReinstateRecordCreationParent | — |
| 23 | `PractitionerReinstateVendorForm_English` | Yes | `force-app/main/default/omniScripts/PRM_PractitionerReinstateVendorForm_English_5.os-meta.xml` | `PRM_CaseDataManager__c`, `PRM_ProgramParticipation__c` | PRM_PractitionerReinstateVendorParent | — |
| 24 | `PractitionerTerminationForm_English` | Yes | `force-app/main/default/omniScripts/PRM_PractitionerTerminationForm_English_31.os-meta.xml` | `PRM_CaseDataManager__c`, `PRM_ProgramParticipation__c` | PRM_PractitionerTerminationRecordsUpdateParent | — |
| 25 | `PrimarySourceVerificationReview_English` | Yes | `force-app/main/default/omniScripts/PRM_PrimarySourceVerificationReview_English_50.os-meta.xml` | `PRM_CaseDataManager__c` | PRM_ReviewPSVCaseRecordsUpdateParent | — |
| 26 | `ProviderChangeForm_English` | Yes | `force-app/main/default/omniScripts/PRM_ProviderChangeForm_English_81.os-meta.xml` | `PRM_CaseDataManager__c` | PRM_CreateRecordsPCFParent | — |
| 27 | `ProviderChangePDAUpdate_English` | Yes | `force-app/main/default/omniScripts/PRM_ProviderChangePDAUpdate_English_31.os-meta.xml` | `PRM_ProgramParticipation__c` | PRM_ProviderChangePDAUpdatesParent | — |
| 28 | `RecredQC_English` | Yes | `force-app/main/default/omniScripts/PRM_RecredQC_English_12.os-meta.xml` | `PRM_CaseDataManager__c` | PRM_ReviewPSVCaseRecordsUpdateParent | — |
| 29 | `ReviewHACAC_English` | Yes | `force-app/main/default/omniScripts/PRM_ReviewHACAC_English_6.os-meta.xml` | `PRM_ContactMethod__c` | PRM_DataUpdationforHAPACCommitteeReviewParent | — |
| 30 | `Supplier Network Creation_English` | Yes | `force-app/main/default/omniScripts/PRM_SupplierNetworkCreation_English_4.os-meta.xml` | `PRM_AccountContractEntity__c`, `PRM_CaseDataManager__c` | PRM_IPSupplierNetworkRecordCreationParent | — |
| 31 | `UpdatePrimaryPracticeLocation_English` | Yes | `force-app/main/default/omniScripts/PRM_UpdatePrimaryPracticeLocation_English_8.os-meta.xml` | `PRM_CaseDataManager__c` | PRM_UpdatePrimaryPracticeLocationParent | — |

## Affected OmniScripts grouped by MD-child target object

### `PRM_AccountContractEntity__c` (4 OmniScript(s))

- `AccountCreation_English`
- `ContractHierarchy_English`
- `PRM_PDMManualChanges_English`
- `Supplier Network Creation_English`

### `PRM_CaseDataManager__c` (24 OmniScript(s))

- `AccountCreation_English`
- `AccountTerminationForm_English`
- `AddAdditionalGroups_English`
- `AncillaryProviderForm_English`
- `ContractHierarchy_English`
- `Manage Practice Location Bundles_English`
- `NonParProviderRegistration_English`
- `PDMManualUpdateFHNaticPractitioner_English`
- `PDMManualUpdatePracticeLocation_English`
- `PDMManualUpdateVendorAccount_English`
- `PDMManualUpdate_English`
- `PRMOffCycleVerification_English`
- `PRMPracticeLocationReinstate_English`
- `PSVSubOsTxnyRole_English`
- `PractitionerCreation_English`
- `PractitionerParticipationForm_English`
- `PractitionerReinstateForm_English`
- `PractitionerReinstateVendorForm_English`
- `PractitionerTerminationForm_English`
- `PrimarySourceVerificationReview_English`
- `ProviderChangeForm_English`
- `RecredQC_English`
- `Supplier Network Creation_English`
- `UpdatePrimaryPracticeLocation_English`

### `PRM_CaseManagerAssociation__c` (2 OmniScript(s))

- `AddAncillaryPLAndBusinessLicense_English`
- `AncillaryProviderForm_English`

### `PRM_ContactMethod__c` (6 OmniScript(s))

- `AncillaryPSVForm_English`
- `AttestationFlow_English`
- `PRMNonParReview_English`
- `PRMPracticeLocationReinstate_English`
- `PRM_PDMManualChanges_English`
- `ReviewHACAC_English`

### `PRM_ProgramParticipation__c` (10 OmniScript(s))

- `AccountTerminationForm_English`
- `PDMManualUpdateFHNaticPractitioner_English`
- `PDMManualUpdatePracticeLocation_English`
- `PDMManualUpdateVendorAccount_English`
- `PDMManualUpdate_English`
- `PRMPracticeLocationReinstate_English`
- `PRM_PDMManualChanges_English`
- `PractitionerReinstateVendorForm_English`
- `PractitionerTerminationForm_English`
- `ProviderChangePDAUpdate_English`

## DataRaptor Loads writing to MD-child objects

| DataRaptor | Target object(s) |
|---|---|
| `PRMCaseMgrCaseDataMgrPDM` | PRM_CaseDataManager__c |
| `PRMCreateCaseDatamanager` | PRM_CaseDataManager__c |
| `PRMDRAccountContractHierarchyCreateRecord` | PRM_AccountContractEntity__c |
| `PRMDRAccountContractHierarchyRecordCreation` | PRM_AccountContractEntity__c |
| `PRMDRCreateAncillaryAdditionalAddressRecords` | PRM_CaseManagerAssociation__c |
| `PRMDRCreateAncillaryHCFacilityLocationAddress` | PRM_CaseManagerAssociation__c |
| `PRMDRCreateBusinessLicenseForAncillaryFacilities` | PRM_CaseManagerAssociation__c |
| `PRMDRCreateCDMForPractitioner` | PRM_CaseDataManager__c |
| `PRMDRCreateCaseDataManagerPLTermination` | PRM_CaseDataManager__c |
| `PRMDRLoadContractEntity` | PRM_AccountContractEntity__c |
| `PRMDRLoadHCFAssociation` | PRM_CaseDataManager__c |
| `PRMDRLoadInfoCodeProgramParPracticeToPrac` | PRM_ProgramParticipation__c |
| `PRMDRLoadInfoCodeProgramParticipationHPFacility` | PRM_ProgramParticipation__c |
| `PRMDRLoadManualHCFAssociations` | PRM_CaseDataManager__c |
| `PRMDRLoadPracticeLocationProgramParticipation` | PRM_ProgramParticipation__c |
| `PRMDRLoadProgramParticipation` | PRM_ProgramParticipation__c |
| `PRMDRLoadSaveLMSDetails` | PRM_CaseDataManager__c, PRM_ProgramParticipation__c |
| `PRMDRLoadUpdateCaseDataMgr` | PRM_CaseDataManager__c |
| `PRMDRLoadUpdateProgParticipation` | PRM_ProgramParticipation__c |
| `PRMDRPAlternateContactUpdate` | PRM_ContactMethod__c |
| `PRMDRPCDMCaseManagerLink` | PRM_CaseDataManager__c |
| `PRMDRPCaseDataManager` | PRM_CaseDataManager__c |
| `PRMDRPCaseDataManagerCaseManager` | PRM_CaseDataManager__c |
| `PRMDRPCreateCaseDataManager` | PRM_CaseDataManager__c |
| `PRMDRPCreateCaseManagerAssociation` | PRM_CaseManagerAssociation__c |
| `PRMDRPNpiHistAdrsAccAccRelationConMethod` | PRM_ContactMethod__c |
| `PRMDRPPracLocAddress` | PRM_ContactMethod__c |
| `PRMDRPPracLocSummaryInfoCodeProgPart` | PRM_ProgramParticipation__c |
| `PRMDRPProvFeatureAltContactFacBundleAssoc` | PRM_ContactMethod__c |
| `PRMDRPProvFeatureAltContactProgramParticipation` | PRM_ContactMethod__c, PRM_ProgramParticipation__c |
| `PRMDRUIFCAndProgramParticipation` | PRM_ProgramParticipation__c |
| `PRMDRUpdateAccContHierarchyAltConMethod` | PRM_AccountContractEntity__c, PRM_ContactMethod__c |
| `PRMDRUpdateAccountContractEntity` | PRM_AccountContractEntity__c |
| `PRMDRUpdateProgPartProvFutureLocTimeSlot` | PRM_ProgramParticipation__c |
| `PRMDRUpsertContactMethod` | PRM_ContactMethod__c |
| `PRMLoadIFAPPForAccount` | PRM_ProgramParticipation__c |
| `PRMLoadIdentifierContact` | PRM_ContactMethod__c |
| `PRMLoadManualUpdateCMCDM` | PRM_CaseDataManager__c |
| `PRMLoadManualUpdateDirIndicators` | PRM_CaseDataManager__c |
| `PRMLoadManualUpdateOH` | PRM_CaseDataManager__c |
| `PRMLoadManualUpdatePAS` | PRM_CaseDataManager__c |
| `PRMLoadManualUpdateProgamParticpations` | PRM_CaseDataManager__c, PRM_ProgramParticipation__c |
| `PRMLoadOffCycleCaseMgrDatMgr` | PRM_CaseDataManager__c |
| `PRMLoadPLAProgramParticipations` | PRM_ProgramParticipation__c |
| `PRMLoadPLBundleCaseCaseMgr` | PRM_CaseDataManager__c |
| `PRMLoadPLTBundleCaseCaseMgr` | PRM_CaseDataManager__c |
| `PRMLoadProgramPartUpdate` | PRM_ProgramParticipation__c |
| `PRMLoadProgramParticipation` | PRM_ProgramParticipation__c |
| `PRMUpdateFieldsCaseDataManager` | PRM_CaseDataManager__c |
| `PRMUpdatePDMManualOnCaseManager` | PRM_CaseDataManager__c |
| `PRMUpdateRecNonPar` | PRM_ContactMethod__c |
| `PRMUpdateSummaryInfoCodeAlterContact` | PRM_ContactMethod__c |

## Integration Procedures that (transitively) write to MD-child objects

| IP procedureKey | Reason |
|---|---|
| `PRM_AccountTermination` | DR:PRMDRLoadInfoCodeProgramParPracticeToPrac -> PRM_ProgramParticipation__c, DR:PRMDRLoadInfoCodeProgramParticipationHPFacility -> PRM_ProgramParticipation__c, DR:PRMDRLoadPracticeLocationProgramParticipation -> PRM_ProgramParticipation__c, DR:PRMDRPCreateCaseDataManager -> PRM_CaseDataManager__c |
| `PRM_AccountTerminationContainer` | IP:PRM_AccountTermination |
| `PRM_AccountTypeCreationContainer` | IP:PRM_AccountTypeRecordCreations |
| `PRM_AccountTypeRecordCreations` | DR:PRMDRAccountContractHierarchyCreateRecord -> PRM_AccountContractEntity__c, DR:PRMDRPCaseDataManager -> PRM_CaseDataManager__c |
| `PRM_AddressLogicContainer` | IP:PRM_ExistingPrimaryPracticeLocationLogicDelg, IP:PRM_PractitionerAddressCreation |
| `PRM_AncillaryAddPLAndLicenseCreation` | DR:PRMDRCreateBusinessLicenseForAncillaryFacilities -> PRM_CaseManagerAssociation__c |
| `PRM_AncillaryAddPLAndLicenseCreationParent` | IP:PRM_AncillaryAddPLAndLicenseCreation |
| `PRM_AncillaryFormRecordsCreation` | DR:PRMDRCreateAncillaryAdditionalAddressRecords -> PRM_CaseManagerAssociation__c, DR:PRMDRCreateAncillaryHCFacilityLocationAddress -> PRM_CaseManagerAssociation__c, DR:PRMDRPCaseDataManager -> PRM_CaseDataManager__c, DR:PRMDRPCreateCaseManagerAssociation -> PRM_CaseManagerAssociation__c |
| `PRM_AncillaryFormRecordsCreationParent` | IP:PRM_AncillaryFormRecordsCreation |
| `PRM_AncillaryPSVFormCreation` | DR:PRMDRPAlternateContactUpdate -> PRM_ContactMethod__c |
| `PRM_AncillaryPSVFormCreationParent` | IP:PRM_AncillaryPSVFormCreation |
| `PRM_ContractHierarchyCreationContainer` | IP:PRM_ContractHierarchyCreations |
| `PRM_ContractHierarchyCreations` | DR:PRMDRLoadContractEntity -> PRM_AccountContractEntity__c, DR:PRMDRPCaseDataManager -> PRM_CaseDataManager__c, DR:PRMDRUpdateAccountContractEntity -> PRM_AccountContractEntity__c |
| `PRM_CreateAdditionalGroups` | IP:PRM_CreatePractitionerAddressRecords |
| `PRM_CreateAdditionalGroupsParent` | IP:PRM_CreateAdditionalGroups |
| `PRM_CreateContactScreenRecords` | DR:PRMUpdateFieldsCaseDataManager -> PRM_CaseDataManager__c |
| `PRM_CreateContactScreenRecordsContainer` | IP:PRM_CreateContactScreenRecords |
| `PRM_CreateParFormRecords` | IP:PRM_CreateContactScreenRecords, IP:PRM_CreatePractitionerAddressRecords, IP:PRM_CreateProviderScreenRecords, IP:PRM_PractitionerScreenExistingNPIRecordUpdation, IP:PRM_PractitionerScreenRecordCreation |
| `PRM_CreateParFormRecordsContainer` | IP:PRM_CreateParFormRecords |
| `PRM_CreatePractitionerAddressRecords` | DR:PRMDRPCaseDataManager -> PRM_CaseDataManager__c |
| `PRM_CreateProviderScreenRecords` | DR:PRMDRPCaseDataManager -> PRM_CaseDataManager__c |
| `PRM_CreateProviderScreenRecordsContainer` | IP:PRM_CreateProviderScreenRecords |
| `PRM_CreateRecordsForPCF` | DR:PRMCreateCaseDatamanager -> PRM_CaseDataManager__c, DR:PRMDRPCDMCaseManagerLink -> PRM_CaseDataManager__c |
| `PRM_CreateRecordsPCFParent` | IP:PRM_CreateRecordsForPCF |
| `PRM_DataUpdationforHAPACCommitteeReview` | DR:PRMDRPAlternateContactUpdate -> PRM_ContactMethod__c |
| `PRM_DataUpdationforHAPACCommitteeReviewParent` | IP:PRM_DataUpdationforHAPACCommitteeReview |
| `PRM_DelegatedPractitionerCreation` | DR:PRMDRCreateCDMForPractitioner -> PRM_CaseDataManager__c, DR:PRMDRPCDMCaseManagerLink -> PRM_CaseDataManager__c |
| `PRM_ExistingPrimaryPracticeLocationLogic` | DR:PRMDRPCaseDataManager -> PRM_CaseDataManager__c |
| `PRM_ExistingPrimaryPracticeLocationLogicDelg` | DR:PRMDRPCaseDataManager -> PRM_CaseDataManager__c |
| `PRM_IPSupplierNetworkRecordCreation` | DR:PRMDRAccountContractHierarchyRecordCreation -> PRM_AccountContractEntity__c, DR:PRMDRPCaseDataManager -> PRM_CaseDataManager__c |
| `PRM_IPSupplierNetworkRecordCreationParent` | IP:PRM_IPSupplierNetworkRecordCreation |
| `PRM_ManageHCFBundleAndAssociations` | DR:PRMDRPCaseDataManager -> PRM_CaseDataManager__c |
| `PRM_ManageHCFBundleAssParents` | IP:PRM_ManageHCFBundleAndAssociations |
| `PRM_ManualChangePDAUpdateParent` | IP:PRM_ManualChangePDAUpdates |
| `PRM_ManualChangePDAUpdates` | DR:PRMDRUpdateAccContHierarchyAltConMethod -> PRM_AccountContractEntity__c, DR:PRMDRUpdateAccContHierarchyAltConMethod -> PRM_ContactMethod__c, DR:PRMDRUpdateProgPartProvFutureLocTimeSlot -> PRM_ProgramParticipation__c |
| `PRM_NonParRecordCreationContainer` | IP:PRM_NonParRecordCreations |
| `PRM_NonParRecordCreations` | DR:PRMDRPCaseDataManager -> PRM_CaseDataManager__c |
| `PRM_OffCycleRecordCreation` | DR:PRMLoadOffCycleCaseMgrDatMgr -> PRM_CaseDataManager__c |
| `PRM_OffCycleRecordCreationParent` | IP:PRM_OffCycleRecordCreation |
| `PRM_PDMCOIHelper` | DR:PRMLoadManualUpdateCMCDM -> PRM_CaseDataManager__c |
| `PRM_PDMLinkUnlinkPracticeLocationHelper` | IP:PRM_PDMRecordsCreationLMSPlus |
| `PRM_PDMPLRecordsCreationHelper` | DR:PRMDRLoadHCFAssociation -> PRM_CaseDataManager__c, DR:PRMDRLoadManualHCFAssociations -> PRM_CaseDataManager__c, DR:PRMLoadManualUpdateDirIndicators -> PRM_CaseDataManager__c, DR:PRMLoadManualUpdateOH -> PRM_CaseDataManager__c, DR:PRMLoadManualUpdatePAS -> PRM_CaseDataManager__c |
| `PRM_PDMPractitionerRecordsCreation` | DR:PRMCreateCaseDatamanager -> PRM_CaseDataManager__c, DR:PRMDRPCDMCaseManagerLink -> PRM_CaseDataManager__c |
| `PRM_PDMPractitionerRecordsCreationParent` | IP:PRM_PDMPractitionerRecordsCreation |
| `PRM_PDMRecordsCreation` | DR:PRMCreateCaseDatamanager -> PRM_CaseDataManager__c, DR:PRMDRPCDMCaseManagerLink -> PRM_CaseDataManager__c, DR:PRMLoadProgramParticipation -> PRM_ProgramParticipation__c |
| `PRM_PDMRecordsCreationForVendorAccount` | DR:PRMCreateCaseDatamanager -> PRM_CaseDataManager__c, DR:PRMDRPCDMCaseManagerLink -> PRM_CaseDataManager__c, DR:PRMLoadProgramParticipation -> PRM_ProgramParticipation__c |
| `PRM_PDMRecordsCreationForVendorAccountParent` | IP:PRM_PDMRecordsCreationForVendorAccount |
| `PRM_PDMRecordsCreationHelper` | DR:PRMLoadIFAPPForAccount -> PRM_ProgramParticipation__c, DR:PRMLoadManualUpdateCMCDM -> PRM_CaseDataManager__c, DR:PRMLoadManualUpdateProgamParticpations -> PRM_CaseDataManager__c, DR:PRMLoadManualUpdateProgamParticpations -> PRM_ProgramParticipation__c, DR:PRMLoadPLAProgramParticipations -> PRM_ProgramParticipation__c |
| `PRM_PDMRecordsCreationLMSPlus` | DR:PRMDRLoadUpdateCaseDataMgr -> PRM_CaseDataManager__c, DR:PRMDRLoadUpdateProgParticipation -> PRM_ProgramParticipation__c |
| `PRM_PDMRecordsCreationParent` | IP:PRM_PDMRecordsCreation |
| `PRM_PDMRecordsCreationPracLocation` | DR:PRMCreateCaseDatamanager -> PRM_CaseDataManager__c, DR:PRMDRPCDMCaseManagerLink -> PRM_CaseDataManager__c |
| `PRM_PDMRecordsCreationPracLocationParent` | IP:PRM_PDMRecordsCreationPracLocation |
| `PRM_PDMRecordsPractitionerCreationHelper` | DR:PRMCaseMgrCaseDataMgrPDM -> PRM_CaseDataManager__c |
| `PRM_PDMUnlinkPracticeLocationHelper` | IP:PRM_PDMRecordsCreationLMSPlus |
| `PRM_PLBundleRecordCreation` | DR:PRMLoadPLBundleCaseCaseMgr -> PRM_CaseDataManager__c, DR:PRMLoadPLTBundleCaseCaseMgr -> PRM_CaseDataManager__c |
| `PRM_PLBundleRecordCreationParent` | IP:PRM_PLBundleRecordCreation |
| `PRM_PractitionerAddressCreation` | DR:PRMDRPCaseDataManager -> PRM_CaseDataManager__c |
| `PRM_PractitionerCreation` | DR:PRMDRCreateCDMForPractitioner -> PRM_CaseDataManager__c, DR:PRMDRPCDMCaseManagerLink -> PRM_CaseDataManager__c |
| `PRM_PractitionerCreationContainer` | IP:PRM_DelegatedPractitionerCreation, IP:PRM_PractitionerCreation |
| `PRM_PractitionerReinstateVendorParent` | IP:PRM_PractitionerReinstateVendorUpdate |
| `PRM_PractitionerReinstateVendorUpdate` | DR:PRMDRPCaseDataManagerCaseManager -> PRM_CaseDataManager__c, DR:PRMDRPPracLocSummaryInfoCodeProgPart -> PRM_ProgramParticipation__c |
| `PRM_PractitionerScreenExistingNPIRecordUpdation` | DR:PRMDRPCaseDataManager -> PRM_CaseDataManager__c |
| `PRM_PractitionerScreenRecordCreation` | DR:PRMDRPCaseDataManager -> PRM_CaseDataManager__c |
| `PRM_PractitionerScreenRecordCreationContainer` | IP:PRM_PractitionerScreenRecordCreation |
| `PRM_PractitionerTerminationRecordsUpdate` | DR:PRMDRUIFCAndProgramParticipation -> PRM_ProgramParticipation__c, DR:PRMUpdatePDMManualOnCaseManager -> PRM_CaseDataManager__c |
| `PRM_PractitionerTerminationRecordsUpdateParent` | IP:PRM_PractitionerTerminationRecordsUpdate |
| `PRM_ProviderChangePDAUpdates` | IP:PRM_ProviderChangePDAUpdatesHelper |
| `PRM_ProviderChangePDAUpdatesHelper` | IP:PRM_TerminateAccountAndFacilityRelations |
| `PRM_ProviderChangePDAUpdatesParent` | IP:PRM_ProviderChangePDAUpdates |
| `PRM_ReCredHelper` | DR:PRMDRPCaseDataManager -> PRM_CaseDataManager__c |
| `PRM_ReinstatePracticeLocation` | DR:PRMDRPCaseDataManagerCaseManager -> PRM_CaseDataManager__c, DR:PRMDRPPracLocAddress -> PRM_ContactMethod__c |
| `PRM_ReinstatePracticeLocationParent` | IP:PRM_ReinstatePracticeLocation |
| `PRM_ReinstateRecordCreation` | DR:PRMDRPCaseDataManager -> PRM_CaseDataManager__c |
| `PRM_ReinstateRecordCreationParent` | IP:PRM_ReinstateRecordCreation |
| `PRM_RequestDeniedRecordsUpdate` | DR:PRMDRPNpiHistAdrsAccAccRelationConMethod -> PRM_ContactMethod__c |
| `PRM_ReviewPSVCaseRecordsUpdate` | DR:PRMDRPCaseDataManager -> PRM_CaseDataManager__c |
| `PRM_ReviewPSVCaseRecordsUpdateParent` | IP:PRM_ReviewPSVCaseRecordsUpdate |
| `PRM_ReviewRecordsUpdate` | DR:PRMUpdateRecNonPar -> PRM_ContactMethod__c |
| `PRM_ReviewRecordsUpdateParent` | IP:PRM_ReviewRecordsUpdate |
| `PRM_TerminateAccountAndFacilityRelations` | DR:PRMLoadProgramPartUpdate -> PRM_ProgramParticipation__c |
| `PRM_TerminateCrossRefFacilities` | DR:PRMLoadIdentifierContact -> PRM_ContactMethod__c, DR:PRMLoadProgramPartUpdate -> PRM_ProgramParticipation__c |
| `PRM_TerminateCrossRefFacilitiesParent` | IP:PRM_TerminateCrossRefFacilities |
| `PRM_UpdateAttestationData` | DR:PRMDRUpsertContactMethod -> PRM_ContactMethod__c |
| `PRM_UpdateAttestationDataParent` | IP:PRM_UpdateAttestationData |
| `PRM_UpdatePracLocSummaryInfoCodeProgPart` | DR:PRMDRPPracLocSummaryInfoCodeProgPart -> PRM_ProgramParticipation__c |
| `PRM_UpdatePrimaryPracticeLocation` | DR:PRMUpdatePDMManualOnCaseManager -> PRM_CaseDataManager__c |
| `PRM_UpdatePrimaryPracticeLocationParent` | IP:PRM_UpdatePrimaryPracticeLocation |
