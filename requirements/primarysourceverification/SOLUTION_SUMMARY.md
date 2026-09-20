# PSV Case Closure - Large Practice Location Volume Solution

## Problem Statement

During the **Primary Source Verification (PSV) case closure** process, when creating a QC Review case:
- The system attempts to process **ALL practice locations from CAQH** 
- This can result in **hundreds of locations**
- The OmniScript/Integration Procedure **times out or fails** due to volume

## What Gets Updated During PSV Case Closure

### IndividualApplication (Case Manager)
**20+ PSV verification fields including:**
- `PRM_ServiceAreaPSV__c` - Service Area Verification
- `PRM_LicensePSV__c` - License Verification
- `PRM_SpecialtyPSV__c` - Specialty Verification
- Plus 15+ other verification status fields
- Stage, PSV Outcome, Medical Director Review flag
- Latest Case link

### Related Objects (Based on Verification Status)
1. **Case** - Closes PSV case, creates new QC case
2. **ContentNote** - Adds notes to Case Manager
3. **BusinessLicense** - State/DEA/CDS licenses (if "Data Looks Good")
4. **PractitionerRole** - Taxonomies/specialties (if "Data Looks Good")
5. **PersonEducation** - Education records (if "Data Looks Good")
6. **BoardCertification** - Board certs (if "Data Looks Good")
7. **HealthcarePractitionerFacility** - ⚠️ **PROBLEM AREA** - Practice locations (if "Data Looks Good")
8. **Identifier** - CAQH ID (if "Data Looks Good")

---

## Solution: Asynchronous Practice Location Processing

### Architecture

```
┌──────────────────────────────┐
│  PSV OmniScript Completes    │
└──────────────┬───────────────┘
               │
               v
      ┌────────────────┐
      │ Count Locations│
      └────────┬───────┘
               │
               v
       ┌──────────────┐
       │ > 20 Locs?   │
       └──┬────────┬──┘
          │        │
     NO   │        │   YES
          │        │
          v        v
    ┌─────────┐  ┌────────────────────┐
    │Sync     │  │ Async Processing   │
    │Process  │  │ (Queueable Apex)   │
    │(Current)│  │                    │
    └────┬────┘  └─────────┬──────────┘
         │                 │
         v                 v
    ┌────────────────────────────┐
    │ PSV Case Closed            │
    │ QC Case Created            │
    │ Case Manager Updated       │
    └────────────────────────────┘
         │                 │
         v                 v
    ┌─────────┐      ┌──────────────┐
    │ Done    │      │ Process in   │
    └─────────┘      │ batches of 50│
                     └──────┬───────┘
                            │
                            v
                     ┌─────────────────┐
                     │ Update Status   │
                     │ "Completed"     │
                     └─────────────────┘
```

---

## Implementation Components

### 1. Apex Classes (Created)
**File:** `PracticeLocationBatchProcessor.apex`

**Classes:**
- `PracticeLocationBatchProcessor` - Queueable class that processes locations in batches
- `PracticeLocationProcessorHelper` - Invocable method wrapper for IP calls

**Features:**
- ✅ Processes 50 locations per batch
- ✅ Chains batches using Queueable
- ✅ Handles duplicates via external IDs
- ✅ Creates/updates: HealthcareFacility, LocationAddress, HealthcarePractitionerFacility
- ✅ Error handling and logging
- ✅ Status tracking on Case Manager

### 2. Custom Fields Required
Add to **IndividualApplication** object:

```
- PRM_PracticeLocationProcessingStatus__c (Picklist)
  Values: "Not Started", "Processing", "Completed", "Error"

- PRM_PracticeLocationProcessingStarted__c (DateTime)

- PRM_PracticeLocationProcessedDate__c (DateTime)

- PRM_PracticeLocationProcessingError__c (Long Text Area)
```

### 3. Integration Procedure Changes
**IP:** `PRM_ReviewPSVCaseRecordsUpdate`

**New Elements:**
1. `SV_CountPracticeLocations` - Count and stringify locations
2. `CB_CheckPracticeLocationVolume` - Route based on count
3. `IPProcessPracticeLocationsAsync` - Call async processing
4. `SV_AsyncProcessingNote` - Update note when async

**Modified Elements:**
- `SetRecordPSVQC` - Only include addresses if ≤ 20 locations

### 4. New Integration Procedure
**Name:** `PRM_ProcessPracticeLocationsAsync`

**Purpose:** Wrapper to call Invocable Apex from IP

**Elements:**
- Set Values (prepare input)
- Apex Action (call `processPracticeLocationsAsync`)
- Response

---

## Benefits

### 1. **No More Timeouts**
- Large volumes processed asynchronously
- No transaction time limits
- Queueable chains handle unlimited volume

### 2. **Fast Case Closure**
- PSV case closes immediately
- QC case created immediately
- User can continue working

### 3. **Transparent Processing**
- Status tracked on Case Manager
- Notes indicate async processing
- Error handling with retry capability

### 4. **Backward Compatible**
- Low volumes (≤ 20) process synchronously as before
- No change to existing behavior for small datasets
- Can adjust threshold (20, 50, 100, etc.)

### 5. **Error Recovery**
- Errors logged to Case Manager
- Manual retry script available
- Can fix data and reprocess

---

## Deployment Steps

### Phase 1: Setup
1. ✅ Create custom fields on IndividualApplication
2. ✅ Deploy Apex classes
3. ✅ Write test classes (70%+ coverage required)
4. ✅ Deploy to Sandbox

### Phase 2: Integration Procedure Changes
1. ✅ Create new IP: `PRM_ProcessPracticeLocationsAsync`
2. ✅ Modify IP: `PRM_ReviewPSVCaseRecordsUpdate`
   - Add counting element
   - Add conditional branch
   - Add async call element
   - Update SetRecord element
3. ✅ Test in Sandbox

### Phase 3: Testing
1. ✅ Test with ≤ 20 locations (should be synchronous)
2. ✅ Test with > 20 locations (should be async)
3. ✅ Test with 100+ locations (high volume)
4. ✅ Test error scenarios
5. ✅ Test manual retry

### Phase 4: Production Deployment
1. ✅ Deploy Apex classes to Production
2. ✅ Create custom fields in Production
3. ✅ Deploy Integration Procedures
4. ✅ Monitor first 10 cases closely
5. ✅ Document in runbook

---

## Monitoring

### Check for Stuck Records
```apex
SELECT Id, Name, PRM_PracticeLocationProcessingStatus__c,
       PRM_PracticeLocationProcessingStarted__c
FROM IndividualApplication
WHERE PRM_PracticeLocationProcessingStatus__c = 'Processing'
  AND PRM_PracticeLocationProcessingStarted__c < LAST_N_HOURS:2
```

### Check Queueable Jobs
```apex
SELECT Id, Status, NumberOfErrors, CreatedDate
FROM AsyncApexJob
WHERE ApexClass.Name = 'PracticeLocationBatchProcessor'
  AND Status IN ('Queued', 'Processing')
ORDER BY CreatedDate DESC
```

### Manual Retry (if needed)
See `PracticeLocationBatchProcessor.apex` for retry script at bottom of file.

---

## Rollback Plan

If issues arise:

1. **Quick Disable:** Change conditional branch to always route to "Low Volume" path
2. **Increase Threshold:** Change from 20 to 50 or 100
3. **Full Rollback:** Deactivate new elements, restore original configuration

---

## Files Created

1. **PSV_Case_Closure_Field_Updates.md** - Complete field mapping documentation
2. **PracticeLocationBatchProcessor.apex** - Apex implementation
3. **Integration_Procedure_Modifications.md** - Detailed IP change instructions
4. **SOLUTION_SUMMARY.md** - This file

---

## Next Steps

1. ✅ Review Apex code with dev team
2. ✅ Add external ID fields if they don't exist:
   - `HealthcareFacility.PRM_CAQHLocationID__c`
   - `LocationAddress.PRM_CAQHAddressID__c`
   - `HealthcarePractitionerFacility.PRM_CAQHLocationID__c`
3. ✅ Write test classes
4. ✅ Deploy to Sandbox
5. ✅ Test thoroughly
6. ✅ Update documentation
7. ✅ Deploy to Production

---

## Questions or Issues?

Contact your Salesforce development team or refer to the detailed documentation in the accompanying files.
