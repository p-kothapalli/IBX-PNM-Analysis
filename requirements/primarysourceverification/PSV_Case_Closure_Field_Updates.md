# Primary Source Verification (PSV) Case Closure - Field Updates

## Overview
When closing a PSV case and creating a QC Review case in the `PrimarySourceVerificationReview` omniscript, the system updates multiple objects through the `PRM_ReviewPSVCaseRecordsUpdateParent` Integration Procedure.

## Objects Being Updated

### 1. **IndividualApplication (Case Manager)** - Main Update via `PRMUpdateIDCaseCaseMgr`

#### PSV Verification Fields (Read from Case Manager, Written Back)
- `PRM_ServiceAreaPSV__c` - Service Area Verification status
- `PRM_SpecialtyPSV__c` - Specialty Verification status
- `PRM_LicensePSV__c` - License Verification status
- `PRM_CAQHAttestation__c` - CAQH Attestation status
- `PRM_EducationPSV__c` - Education Verification status
- `PRM_DEAPSV__c` - DEA Verification status
- `PRM_CDSPSV__c` - CDS Verification status
- `PRM_InsurancePSV__c` - Insurance Verification status
- `PRM_WorkHistoryPSV__c` - Work History Verification status
- `PRM_FSMBPSV__c` - FSMB Verification status
- `PRM_BoardCertificationPSV__c` - Board Certification Verification status
- `PRM_AdmittingPrivilegesReview__c` - Admitting Privileges Review status
- `PRM_DisclosureReview__c` - Disclosure Review status
- `PRM_CMSPreclusionReview__c` - CMS Preclusion Review status
- `PRM_SAMReview__c` - SAM Review status
- `PRM_MedicareOptOutReview__c` - Medicare Opt-Out Review status
- `PRM_NPDBVerified__c` - NPDB Verified status
- `PRM_NPDBVerifiedOn__c` - NPDB Verified date
- `PRM_ContractStatus__c` - Contract Status

#### Additional Formula-Derived Fields
- `PRM_LicenseVerification__c` - License Verification (formula-based)
- `PRM_SpecialtyVerification__c` - Specialty Verification (formula-based)
- `PRM_DEAVerification__c` - DEA Verification (formula-based)
- `PRM_CDSVerification__c` - CDS Verification (formula-based)
- `PRM_EducationVerification__c` - Education Verification (formula-based)
- `PRM_MalpracticeCoverageVerification__c` - Malpractice Coverage Verification
- `PRM_WorkHistoryVerification__c` - Work History Verification (formula-based)
- `PRM_AttestationVerification__c` - Attestation Verification

#### Case Flow Management Fields
- `PRM_Stage__c` - Current stage ("QC Review" or "Application Review")
- `PRM_PSVOutcome__c` - PSV outcome ("PSV QC", "Medical Director Review", or "Return to App Review")
- `PRM_MedicalDirectorReview__c` - Medical Director Review flag (true/false)
- `LatestCase` - ID of the newly created case

#### Other Fields
- `PRM_RecredTerm__c` - Recredentialing termination flag (for recred flow)
- `PRM_RecredUpdate__c` - Recredentialing update flag (for recred flow)
- `PRM_Decision_Date__c` - Decision date
- `PRM_DenialReason__c` - Denial reason
- `PRM_ErrorReasons__c` - Error reasons
- `PRM_FormCompletedBy__c` - Form completed by
- `PRM_IsRoundRobinLogic__c` - Round robin logic flag
- `PRM_NPDBIssue__c` - NPDB issue flag
- `PRM_NPDBVerification__c` - NPDB verification status
- `OwnerId` - Owner of the IndividualApplication

### 2. **Case** - PSV Case Closure via `PRMUpdateIDCaseCaseMgr`
- `Id` - Case ID
- `Status` - Set to "Closed"

### 3. **Case** - New QC Review Case Creation via `PRMCreateNewCase`
- `AccountId` - Account (Practitioner) ID
- `ContactId` - Contact ID
- `Owner` - Case owner (queue or user)
- `OwnerName` - "PRM_CredentialingQCQueue" (for PSV QC) or "PRM_CredentialingQCQueue" (for MDR)
- `PRM_CaseManager__c` - Case Manager (IndividualApplication) ID
- `PRM_ExpeditedCred__c` - Expedited credentialing flag
- `Priority` - "High" (if expedited) or "Standard"
- `RecordTypeId` - Record type for PRM case
- `Status` - "New" (for QC) or "Returned" (for App Review return)
- `Type` - "QC Review" or "Application Review"
- `PRM_IsRoundRobinLogic__c` - Round robin assignment flag

### 4. **ContentNote** - Case Notes
- `content` - Note content (from `%ProceedToNote%` or `%ReCredNote%`)
- `entityId` - IndividualApplication ID
- `title` - "PSV to QC Review", "PSV to QC", or "PSV Return to App Review"

### 5. **BusinessLicense** - License Updates (if "Data Looks Good")
**Source:** `%VerifyLicense:BusinessLicensePractitioner%` (SBRD Licenses)
- Multiple license records created/updated via DataRaptor transformations
- Includes State, DEA, and CDS licenses

### 6. **PractitionerRole** - Taxonomy/Specialty Updates (if "Data Looks Good")
**Source:** `%VerifySpecialty:VerifyPractitionerSpecialty%`
- Taxonomy and specialty information
- Updated via `DRTTaxonomy` and `DRPTaxonomy` DataRaptors

### 7. **PersonEducation** - Education Records (if "Data Looks Good")
**Source:** `%EducationVerification:CAQHPersonEducation%`
- Education history from CAQH
- Created/updated via comparison and merge logic

### 8. **BoardCertification** - Board Certification Records (if "Data Looks Good")
**Source:** `%BoardCertificationsStep:CAQHBoardCertification%`
- Board certification records from CAQH
- Includes existing, new, and PSV-specific board certifications
- Updated via complex merge and comparison logic

### 9. **HealthcarePractitionerFacility** - Practice Location Relationships (if "Data Looks Good")
**Source:** `%ServiceAreaVerificationStep:PracticeAddressBlk%`
- **THIS IS THE PROBLEM AREA** - Large volume of CAQH practice locations
- Records created for each practice location
- Links Practitioner to Facility (Healthcare Facility)

### 10. **Identifier** - CAQH Identifier (if "Data Looks Good")
**Source:** `%CAQHSignatureAttestionStep:CAQHAttestationBlk%`
- CAQH ID identifier record
- Created/updated with CAQH information

### 11. **AdverseActionReview** - Adverse Action Review (if applicable)
**Source:** `%MDRFormStep%` (when Medical Director Review is selected)
- Adverse action review records
- Created when proceeding to Medical Director Review

---

## Data Flow Summary

### SetRecordPSVQC (Initial Credentialing)
```json
RecordsToUpdate = {
    "AccountID": Account ID,
    "Addresses": Practice locations (IF ServiceAreaVerification = "Data Looks Good"),
    "AdmittingPrivileges": Admitting privileges (IF AdmittingPrivilegesReview = "Application/Attestation"),
    "BoardCertification": Board certifications (IF BoardCertificationVerification = "Data Looks Good"),
    "CAQHIdentifier": CAQH ID (IF CAQHSignatureAttest = "Data Looks Good"),
    "CDSLicenses": CDS licenses (IF CDSVerification = "Data Looks Good"),
    "Case": { "Id": Case ID, "Status": "Closed" },
    "ContactID": Contact ID,
    "ContentNote": { "content": Note, "entityId": IndApp ID, "title": Note title },
    "DEALicenses": DEA licenses (IF DEAVerification = "Data Looks Good"),
    "FlowType": "PSV",
    "HealthCareProviderID": Healthcare Provider ID,
    "IndividualApplication": { All PSV verification fields },
    "NewCase": { New case details },
    "PersonEducation": Education records (IF EducationVerification = "Data Looks Good"),
    "SBRDLicenses": State licenses (IF LicenseVerification = "Data Looks Good"),
    "Taxonomies": Specialties (IF SpecialtyVerification = "Data Looks Good")
}
```

### SetRecordReCredPSV (Re-credentialing)
Same structure as above, but:
- `"FlowType": "ReCred"`
- Uses `%ReCredServiceAreaVeriFRML%` and other ReCred-specific formulas
- Includes `"PracticeLocationBlock"` for new practice locations added during recred
- Includes `"Attachments"` for recred signature attachments

---

## The Problem: Large Volume of Practice Locations

### Current Issue
When `ServiceAreaVerification = "Data Looks Good"`, the system attempts to create/update:
- **All practice locations from CAQH** via `%ServiceAreaVerificationStep:PracticeAddressBlk%`
- This can result in **hundreds of practice location records**
- The omniscript/integration procedure **times out or fails** due to:
  - Large JSON payload size
  - DML limits
  - Processing time limits

### Current Logic Location
**File:** `IBXQA/vlocity_export/OmniScript/PRM_PrimarySourceVerificationReview_English/PRM_PrimarySourceVerificationReview_English_Element_SetRecordPSVQC.json`

**Line 17:**
```json
"Addresses": "=IF(%ServiceAreaVerification% == \"Data Looks Good\",%ServiceAreaVerificationStep:PracticeAddressBlk%,[])"
```

**Integration Procedure:** `PRM_ReviewPSVCaseRecordsUpdate`
**Element:** `CheckServiceAreaStepRecords` - validates and processes practice locations

---

## Recommended Solutions

### Option 1: Batch Processing with Queueable Apex
Instead of processing all practice locations in the omniscript, trigger an asynchronous job:
- Store practice locations in a staging area
- Process in batches via Queueable Apex
- Update Case Manager status when complete

### Option 2: Filter Practice Locations
Only process:
- Primary practice location
- Locations within service area (specific states/counties)
- Locations marked as active/current by the user

### Option 3: Deferred Processing
- Complete PSV case closure immediately
- Create QC case with "Pending Practice Location Processing" status
- Process practice locations asynchronously
- Auto-update status when complete

### Option 4: Split Service Area Step
- Separate service area verification from practice location updates
- Allow users to verify service area without immediately processing all locations
- Add a "Process Practice Locations" button in QC Review step
