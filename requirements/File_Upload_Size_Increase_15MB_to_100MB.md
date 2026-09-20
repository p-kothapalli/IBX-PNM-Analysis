# File Upload Size Increase: 15MB to 100MB

**Business Requirement**: Update file upload size limitation from 15 MB to 100 MB across all OmniScripts with file upload functionality.

**Date**: 2026-04-08

## Summary

11 OmniScripts have been identified with file upload components that currently enforce a 15 MB file size limit. These need to be updated to support 100 MB file uploads.

---

## Technical Changes Required

### 1. Byte Value Updates
- **Current**: `15728640` (15 * 1024 * 1024 bytes)
- **New**: `104857600` (100 * 1024 * 1024 bytes)

### 2. Display Message Updates
- **Current patterns**:
  - "The total file size must not exceed 15MB."
  - "File must be in PDF or Excel format and file size must not exceed 15mb."
  - "File must be in PDF or Excel format and File size should not exceed 15mb."
  - "File must be in PDF format only and file size must not exceed 15mb."
  
- **Update to**: Replace all instances of "15MB" or "15mb" with "100MB"

---

## OmniScripts Requiring Updates

### 1. PRM_AccountCreation_English

**Description**: Provider account creation omniscript with file upload capability

**Files to Update**:
- `force-app/main/default/omniScripts/PRM_AccountCreation_English_19.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_AccountCreation_English_20.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_AccountCreation_English_21.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_AccountCreation_English_22.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_AccountCreation_English_23.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_AccountCreation_English_24.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_AccountCreation_English_25.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_AccountCreation_English_26.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_AccountCreation_English_27.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_AccountCreation_English_29.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_AccountCreation_English_30.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_AccountCreation_English_31.os-meta.xml`

**Changes**:
- Update validation rule bytes from `15728640` to `104857600`
- Update message: "File must be in PDF or Excel format and File size should not exceed 15mb." → "...100MB."

**Element**: `MSG_PDFFileFormat`

---

### 2. PRM_AncillaryReassessmentPSV_English

**Description**: Ancillary provider reassessment primary source verification

**Files to Update**:
- `force-app/main/default/omniScripts/PRM_AncillaryReassessmentPSV_English_1.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_AncillaryReassessmentPSV_English_2.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_AncillaryReassessmentPSV_English_3.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_AncillaryReassessmentPSV_English_4.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_AncillaryReassessmentPSV_English_5.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_AncillaryReassessmentPSV_English_6.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_AncillaryReassessmentPSV_English_7.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_AncillaryReassessmentPSV_English_8.os-meta.xml`
- Vlocity export files:
  - `vlocity_export/OmniScript/PRM_AncillaryReassessmentPSV_English/PRM_AncillaryReassessmentPSV_English_Element_ErrorMsgBlock.json`
  - `vlocity_export/OmniScript/PRM_AncillaryReassessmentPSV_English/PRM_AncillaryReassessmentPSV_English_Element_SetErrorFileValidation.json`

**Changes**:
- Update message: "File must be in PDF or Excel format and File size should not exceed 15MB." → "...100MB."

**Element**: `ErrorMsgBlock`, `SetErrorFileValidation`

---

### 3. PRM_AncillaryproviderFormDocumentation_English

**Description**: Ancillary provider form documentation with file uploads

**Files to Update**:
- `force-app/main/default/omniScripts/PRM_AncillaryproviderFormDocumentation_English_1.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_AncillaryproviderFormDocumentation_English_2.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_AncillaryproviderFormDocumentation_English_3.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_AncillaryproviderFormDocumentation_English_4.os-meta.xml`
- Vlocity export files:
  - `vlocity_export/OmniScript/PRM_AncillaryproviderFormDocumentation_English/PRM_AncillaryproviderFormDocumentation_English_DataPack.json`
  - `vlocity_export/OmniScript/PRM_AncillaryproviderFormDocumentation_English/PRM_AncillaryproviderFormDocumentation_English_Element_MSG_FileSizeUpto15MB.json`
  - `vlocity_export/OmniScript/PRM_AncillaryproviderFormDocumentation_English/PRM_AncillaryproviderFormDocumentation_English_Element_SetErrorFileValidation.json`
  - `vlocity_export/OmniScript/PRM_AncillaryproviderFormDocumentation_English/PRM_AncillaryproviderFormDocumentation_English_Element_ErrorMsgBlock.json`
  - `vlocity_export/OmniScript/PRM_AncillaryproviderFormDocumentation_English/PRM_AncillaryproviderFormDocumentation_English_Element_UploadDocuments.json`

**Changes**:
- Update validation rule bytes from `15728640` to `104857600`
- Update message: "The total file size must not exceed 15MB." → "...100MB."
- Update error message: "File must be in PDF or Excel format only and file size must not exceed 15MB." → "...100MB."

**Elements**: `MSG_FileSizeUpto15MB`, `ErrorMsgBlock`, `SetErrorFileValidation`, `UploadDocuments`

---

### 4. PRM_CredentialAppReviewFileLoad_English

**Description**: Credential application review file loading

**Files to Update**:
- `force-app/main/default/omniScripts/PRM_CredentialAppReviewFileLoad_English_1.os-meta.xml`
- Vlocity export files:
  - `vlocity_export/OmniScript/PRM_CredentialAppReviewFileLoad_English/PRM_CredentialAppReviewFileLoad_English_DataPack.json`
  - `vlocity_export/OmniScript/PRM_CredentialAppReviewFileLoad_English/PRM_CredentialAppReviewFileLoad_English_Element_MSG_FileSizeUpto15MB.json`
  - `vlocity_export/OmniScript/PRM_CredentialAppReviewFileLoad_English/PRM_CredentialAppReviewFileLoad_English_Element_SErrorFileValidation.json`
  - `vlocity_export/OmniScript/PRM_CredentialAppReviewFileLoad_English/PRM_CredentialAppReviewFileLoad_English_Element_TBFileErrorMsg.json`

**Changes**:
- Update validation rule bytes from `15728640` to `104857600`
- Update message: "The total file size must not exceed 15MB." → "...100MB."
- Update error message: "File must be in PDF format only and file size must not exceed 15mb." → "...100MB."

**Elements**: `MSG_FileSizeUpto15MB`, `SErrorFileValidation`, `TBFileErrorMsg`

---

### 5. PRM_FileUploadOS_English

**Description**: Generic file upload omniscript

**Files to Update**:
- `force-app/main/default/omniScripts/PRM_FileUploadOS_English_2.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_FileUploadOS_English_4.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_FileUploadOS_English_5.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_FileUploadOS_English_6.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_FileUploadOS_English_7.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_FileUploadOS_English_8.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_FileUploadOS_English_9.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_FileUploadOS_English_10.os-meta.xml`
- Vlocity export files:
  - `vlocity_export/OmniScript/PRM_FileUploadOS_English/PRM_FileUploadOS_English_Element_SerErrorFileValidation.json`
  - `vlocity_export/OmniScript/PRM_FileUploadOS_English/PRM_FileUploadOS_English_Element_TBFileErrorMsg.json`

**Changes**:
- Update error message: "File must be in PDF or Excel format only and file size must not exceed 15mb." → "...100MB."

**Elements**: `SerErrorFileValidation`, `TBFileErrorMsg`

---

### 6. PRM_InitialCredentialAppReview_English

**Description**: Initial credential application review

**Files to Update**:
- `force-app/main/default/omniScripts/PRM_InitialCredentialAppReview_English_22.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_InitialCredentialAppReview_English_23.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_InitialCredentialAppReview_English_24.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_InitialCredentialAppReview_English_25.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_InitialCredentialAppReview_English_26.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_InitialCredentialAppReview_English_27.os-meta.xml`

**Changes**:
- Update message: "The total file size must not exceed 15MB." → "...100MB."

**Element**: `MSG_FileSizeUpto15MB`

---

### 7. PRM_NonParProviderRegistration_English

**Description**: Non-par provider registration with file uploads

**Files to Update**:
- `force-app/main/default/omniScripts/PRM_NonParProviderRegistration_English_44.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_NonParProviderRegistration_English_45.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_NonParProviderRegistration_English_46.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_NonParProviderRegistration_English_47.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_NonParProviderRegistration_English_48.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_NonParProviderRegistration_English_49.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_NonParProviderRegistration_English_50.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_NonParProviderRegistration_English_51.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_NonParProviderRegistration_English_52.os-meta.xml`
- Vlocity export files:
  - `vlocity_export/OmniScript/PRM_NonParProviderRegistration_English/PRM_NonParProviderRegistration_English_Element_MSG_PDFFileFormat.json`

**Changes**:
- Update validation rule bytes from `15728640` to `104857600`
- Update message: "File must be in PDF or Excel format and File size should not exceed 15mb." → "...100MB."

**Element**: `MSG_PDFFileFormat`

---

### 8. PRM_NonParReview_English

**Description**: Non-par provider review process

**Files to Update**:
- `force-app/main/default/omniScripts/PRM_NonParReview_English_20.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_NonParReview_English_21.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_NonParReview_English_22.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_NonParReview_English_23.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_NonParReview_English_24.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_NonParReview_English_25.os-meta.xml`
- Vlocity export files:
  - `vlocity_export/OmniScript/PRM_NonParReview_English/PRM_NonParReview_English_Element_MSG_PDFFileFormat.json`

**Changes**:
- Update validation rule bytes from `15728640` to `104857600`
- Update message: "File must be in PDF or Excel format and File size should not exceed 15mb." → "...100MB."

**Element**: `MSG_PDFFileFormat`

---

### 9. PRM_OffCycleVerification_English

**Description**: Off-cycle verification process with document uploads

**Files to Update**:
- `force-app/main/default/omniScripts/PRM_OffCycleVerification_English_26.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_OffCycleVerification_English_27.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_OffCycleVerification_English_28.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_OffCycleVerification_English_29.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_OffCycleVerification_English_30.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_OffCycleVerification_English_31.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_OffCycleVerification_English_32.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_OffCycleVerification_English_33.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_OffCycleVerification_English_34.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_OffCycleVerification_English_35.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_OffCycleVerification_English_36.os-meta.xml`
- Vlocity export files:
  - `vlocity_export/OmniScript/PRM_OffCycleVerification_English/PRM_OffCycleVerification_English_DataPack.json`
  - `vlocity_export/OmniScript/PRM_OffCycleVerification_English/PRM_OffCycleVerification_English_Element_MSG_FileSizeUpto15MB.json`

**Changes**:
- Update validation rule bytes from `15728640` to `104857600` in validateExpression
- Update message: "The total file size must not exceed 15MB." → "...100MB."

**Element**: `MSG_FileSizeUpto15MB`

**Validation Field**: `RoleChangeApproval|1:size`

---

### 10. PRM_PSVSubOsTxnyRole_English

**Description**: Primary source verification sub-omniscript for taxonomy role

**Files to Update**:
- `force-app/main/default/omniScripts/PRM_PSVSubOsTxnyRole_English_1.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_PSVSubOsTxnyRole_English_2.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_PSVSubOsTxnyRole_English_3.os-meta.xml`
- Vlocity export files:
  - `vlocity_export/OmniScript/PRM_PSVSubOsTxnyRole_English/PRM_PSVSubOsTxnyRole_English_Element_SErrorFileValidation.json`
  - `vlocity_export/OmniScript/PRM_PSVSubOsTxnyRole_English/PRM_PSVSubOsTxnyRole_English_Element_TBFileErrorMsgBlk.json`

**Changes**:
- Update error message: "File must be in PDF format only and file size must not exceed 15mb." → "...100MB."

**Elements**: `SErrorFileValidation`, `TBFileErrorMsgBlk`

---

### 11. PRM_PrimarySourceVerificationReview_English

**Description**: Primary source verification review process

**Files to Update**:
- `force-app/main/default/omniScripts/PRM_PrimarySourceVerificationReview_English_35.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_PrimarySourceVerificationReview_English_36.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_PrimarySourceVerificationReview_English_37.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_PrimarySourceVerificationReview_English_38.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_PrimarySourceVerificationReview_English_39.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_PrimarySourceVerificationReview_English_40.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_PrimarySourceVerificationReview_English_41.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_PrimarySourceVerificationReview_English_42.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_PrimarySourceVerificationReview_English_43.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_PrimarySourceVerificationReview_English_44.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_PrimarySourceVerificationReview_English_45.os-meta.xml`
- `force-app/main/default/omniScripts/PRM_PrimarySourceVerificationReview_English_46.os-meta.xml`
- Vlocity export files:
  - `vlocity_export/OmniScript/PRM_PrimarySourceVerificationReview_English/PRM_PrimarySourceVerificationReview_English_Element_SerErrorFileValidationReCred.json`

**Changes**:
- Update error message: "File must be in PDF format only and file size must not exceed 15mb." → "...100MB."

**Element**: `SerErrorFileValidationReCred`

---

## Additional Code Updates

### Test Class Update

**File**: `force-app/main/default/classes/PRM_OmniUtilsTest.cls`

**Line 433**:
```apex
// Current:
input.put('MaxSize',15728640);

// Update to:
input.put('MaxSize',104857600);
```

---

## Implementation Notes

### Validation Logic Location

The file size validation is implemented in the Apex class `PRM_OmniUtils.cls` which:
- Accepts `MaxSize` parameter from OmniScript (line 651)
- Validates uploaded file size against this limit (line 676)
- Returns validation results back to OmniScript

**Code Reference** (`PRM_OmniUtils.cls`):
```apex
Line 634: List<Object> objFiles = (List<Object>) inputMap.get('uploadedFiles');
Line 651: Integer maxFileSize = (Integer) inputMap.get('MaxSize');
Line 675: Integer existingFileSize = (Integer) existingFile.get('size');            
Line 676: if (acceptedFormats.contains(fileExt) && existingFileSize <= maxFileSize) {
```

### Update Approach

1. **Meta XML Files**: Update the `data` attribute in validateExpression from "15728640" to "104857600"
2. **Message Elements**: Update all display text from "15MB" to "100MB"
3. **Vlocity Export Files**: Update both validation rules and messages in JSON format
4. **Test Class**: Update test data to use new file size limit

### Deployment Considerations

- All versions of each OmniScript should be updated for consistency
- Test class should be updated and all tests should pass
- Consider updating all related documentation and user guides
- Verify no custom validation rules or platform limits that might conflict with 100MB uploads
- Check Salesforce file upload limits (typically 2GB for ContentVersion)

---

## Testing Checklist

After implementation, verify:
- [ ] File upload works correctly with files between 15MB and 100MB
- [ ] Validation messages display correctly showing "100MB" limit
- [ ] Files over 100MB are properly rejected with correct error message
- [ ] All existing functionality remains intact
- [ ] Test class `PRM_OmniUtilsTest` passes
- [ ] No performance degradation with larger file uploads
- [ ] UI displays validation messages properly

---

## File Count Summary

- **Total OmniScripts**: 11
- **Total .os-meta.xml files**: 80+
- **Total Vlocity export JSON files**: 15+
- **Test classes**: 1
- **Apex classes with logic**: 1 (PRM_OmniUtils.cls - no changes needed, just accepts MaxSize parameter)

---

## Related Documentation

- OmniScript File Upload Component Documentation
- Salesforce ContentVersion File Size Limits
- PRM_OmniUtils Class Documentation
