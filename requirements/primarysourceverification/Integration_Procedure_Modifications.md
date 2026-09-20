# Integration Procedure Modifications for Async Practice Location Processing

## Overview
This document outlines the modifications needed to the `PRM_ReviewPSVCaseRecordsUpdate` Integration Procedure to handle large volumes of practice locations asynchronously.

---

## Required Custom Fields on IndividualApplication

Add these custom fields to track async processing status:

```text
1. PRM_PracticeLocationProcessingStatus__c (Picklist)
   - Values: "Not Started", "Processing", "Completed", "Error"
   - Default: "Not Started"

2. PRM_PracticeLocationProcessingStarted__c (DateTime)
   - Tracks when processing started

3. PRM_PracticeLocationProcessedDate__c (DateTime)
   - Tracks when processing completed

4. PRM_PracticeLocationProcessingError__c (Long Text Area)
   - Stores error messages if processing fails
```

---

## Modification 1: Add Conditional Branch in Integration Procedure

### Location
**Integration Procedure:** `PRM_ReviewPSVCaseRecordsUpdate`
**After Element:** `CheckServiceAreaStepRecords`

### New Element: `CB_CheckPracticeLocationVolume`
**Type:** Conditional Branch
**Purpose:** Determine if practice locations should be processed synchronously or asynchronously

**Condition:**
```javascript
%CheckServiceAreaStepRecords:PracticeLocationCount% > 20
```

**Branches:**
- **Branch 1 (High Volume):** Route to async processing → `IPProcessPracticeLocationsAsync`
- **Branch 2 (Low Volume):** Continue with existing logic → `DRLoadHCPFRecords`

---

## Modification 2: Add Set Values Element to Count Locations

### Element Name: `SV_CountPracticeLocations`
**Type:** Set Values
**Insert Before:** `CheckServiceAreaStepRecords`

**Configuration:**
```json
{
  "PracticeLocationCount": "=%ServiceAreaVerificationStep:PracticeAddressBlk:length%",
  "PracticeLocationsJson": "=JSON.stringify(%ServiceAreaVerificationStep:PracticeAddressBlk%)"
}
```

---

## Modification 3: Add Integration Procedure Action for Async Processing

### Element Name: `IPProcessPracticeLocationsAsync`
**Type:** Integration Procedure Action
**Integration Procedure:** `PRM_ProcessPracticeLocationsAsync` (new IP)

**Input:**
```json
{
  "CaseManagerId": "%RecordsToUpdate:CaseManagerID%",
  "PracticeLocationsJson": "%SV_CountPracticeLocations:PracticeLocationsJson%",
  "CaseId": "%RecordsToUpdate:Case:Id%",
  "FlowType": "%RecordsToUpdate:FlowType%"
}
```

**Execution Condition:**
```
%CB_CheckPracticeLocationVolume% == 'High Volume'
```

---

## Modification 4: Create New Integration Procedure for Async Call

### Integration Procedure Name: `PRM_ProcessPracticeLocationsAsync`

**Purpose:** Wrapper IP to call the Invocable Apex method

**Elements:**

#### 1. Set Values - Prepare Input
**Name:** `SV_PrepareAsyncInput`
**Type:** Set Values

```json
{
  "caseManagerId": "%CaseManagerId%",
  "practiceLocationsJson": "%PracticeLocationsJson%",
  "caseId": "%CaseId%",
  "flowType": "%FlowType%"
}
```

#### 2. Apex Action - Call Invocable Method
**Name:** `Apex_ProcessPracticeLocations`
**Type:** Apex Action
**Apex Class:** `PracticeLocationProcessorHelper`
**Method:** `processPracticeLocationsAsync`

**Input:**
```json
{
  "requests": [
    {
      "caseManagerId": "%SV_PrepareAsyncInput:caseManagerId%",
      "practiceLocationsJson": "%SV_PrepareAsyncInput:practiceLocationsJson%",
      "caseId": "%SV_PrepareAsyncInput:caseId%",
      "flowType": "%SV_PrepareAsyncInput:flowType%"
    }
  ]
}
```

#### 3. Response
**Name:** `Response`
**Type:** Response Action

```json
{
  "success": "%Apex_ProcessPracticeLocations:responses|1:success%",
  "message": "%Apex_ProcessPracticeLocations:responses|1:message%"
}
```

---

## Modification 5: Update SetRecordPSVQC Element

### Current Configuration (Line 17):
```json
"Addresses": "=IF(%ServiceAreaVerification% == \"Data Looks Good\",%ServiceAreaVerificationStep:PracticeAddressBlk%,[])"
```

### New Configuration:
```json
"Addresses": "=IF(%ServiceAreaVerification% == \"Data Looks Good\" && %SV_CountPracticeLocations:PracticeLocationCount% <= 20,%ServiceAreaVerificationStep:PracticeAddressBlk%,[])"
```

**Explanation:** Only include addresses in synchronous processing if there are 20 or fewer locations.

---

## Modification 6: Add Note to ContentNote When Async Processing is Used

### Element Name: `SV_AsyncProcessingNote`
**Type:** Set Values
**Execution Condition:** `%CB_CheckPracticeLocationVolume% == 'High Volume'`

**Configuration:**
```json
{
  "RecordsToUpdate:ContentNote:content": "=%RecordsToUpdate:ContentNote:content% + '\n\nPractice locations are being processed asynchronously due to high volume (%SV_CountPracticeLocations:PracticeLocationCount% locations). Processing status can be tracked on the Case Manager record.'",
  "RecordsToUpdate:IndividualApplication:PRM_PracticeLocationProcessingStatus__c": "Processing"
}
```

---

## Modified Integration Procedure Flow

```
┌─────────────────────────────────────┐
│ DRTransformPSVUpdateData            │
└───────────────┬─────────────────────┘
                │
                v
┌─────────────────────────────────────┐
│ SV_CountPracticeLocations           │ ← NEW
│ (Count locations, stringify JSON)   │
└───────────────┬─────────────────────┘
                │
                v
┌─────────────────────────────────────┐
│ CheckServiceAreaStepRecords         │
└───────────────┬─────────────────────┘
                │
                v
┌─────────────────────────────────────┐
│ CB_CheckPracticeLocationVolume      │ ← NEW
│ (Check if > 20 locations)           │
└───────┬───────────────┬─────────────┘
        │               │
        │ Low Volume    │ High Volume
        │ (<= 20)       │ (> 20)
        v               v
┌───────────────┐ ┌─────────────────────────────────┐
│ DRLoadHCPF    │ │ IPProcessPracticeLocationsAsync │ ← NEW
│ Records       │ │ (Enqueue async job)             │
│ (Existing)    │ └─────────────────────────────────┘
└───────┬───────┘
        │
        v
┌─────────────────────────────────────┐
│ DRCreateNewCase                     │
└─────────────────────────────────────┘
        │
        v
┌─────────────────────────────────────┐
│ DRUpdateCaseCaseManager             │
└─────────────────────────────────────┘
        │
        v
┌─────────────────────────────────────┐
│ Response                            │
└─────────────────────────────────────┘
```

---

## Validation & Testing

### Test Scenarios

#### Scenario 1: Low Volume (≤ 20 locations)
- **Expected:** Synchronous processing as before
- **Verify:** All practice locations created immediately
- **Status:** Processing completes in same transaction

#### Scenario 2: High Volume (> 20 locations)
- **Expected:** Async processing initiated
- **Verify:** 
  - Case Manager status = "Processing"
  - Queueable job enqueued
  - Note includes async processing message
  - QC case created immediately
  - Practice locations created in batches over time
  - Final status = "Completed"

#### Scenario 3: Error Handling
- **Expected:** Errors logged and status updated
- **Verify:**
  - Case Manager status = "Error"
  - Error message populated
  - Can retry processing manually

---

## Monitoring & Troubleshooting

### Check Processing Status
```apex
List<IndividualApplication> apps = [
    SELECT Id, Name, PRM_PracticeLocationProcessingStatus__c,
           PRM_PracticeLocationProcessingStarted__c,
           PRM_PracticeLocationProcessedDate__c,
           PRM_PracticeLocationProcessingError__c
    FROM IndividualApplication
    WHERE PRM_PracticeLocationProcessingStatus__c = 'Processing'
    AND PRM_PracticeLocationProcessingStarted__c < LAST_N_HOURS:2
];

System.debug('Stuck records: ' + apps.size());
```

### Check Queueable Jobs
```apex
List<AsyncApexJob> jobs = [
    SELECT Id, Status, NumberOfErrors, CreatedDate,
           CompletedDate, ExtendedStatus
    FROM AsyncApexJob
    WHERE ApexClass.Name = 'PracticeLocationBatchProcessor'
    AND Status IN ('Queued', 'Processing', 'Preparing')
    ORDER BY CreatedDate DESC
    LIMIT 10
];

for (AsyncApexJob job : jobs) {
    System.debug('Job: ' + job.Id + ' | Status: ' + job.Status + ' | Errors: ' + job.NumberOfErrors);
}
```

### Manually Retry Failed Processing
```apex
Id caseManagerId = 'a0X...'; // Replace with actual ID

IndividualApplication app = [
    SELECT Id, PRM_PracticeLocationProcessingError__c
    FROM IndividualApplication
    WHERE Id = :caseManagerId
];

// Get practice locations from CAQH (you'll need to re-fetch or store them)
String practiceLocationsJson = '...'; // Your JSON data

PracticeLocationProcessorHelper.Request req = new PracticeLocationProcessorHelper.Request();
req.caseManagerId = caseManagerId;
req.practiceLocationsJson = practiceLocationsJson;
req.caseId = 'your-case-id';
req.flowType = 'PSV';

List<PracticeLocationProcessorHelper.Response> responses =
    PracticeLocationProcessorHelper.processPracticeLocationsAsync(
        new List<PracticeLocationProcessorHelper.Request>{req}
    );

System.debug('Retry result: ' + responses[0].message);
```

---

## Rollback Plan

If async processing causes issues:

1. **Disable Conditional Branch:**
   - Set `CB_CheckPracticeLocationVolume` condition to always return "Low Volume"
   - This will route all processing through existing synchronous path

2. **Increase Threshold:**
   - Change threshold from 20 to 50 or 100
   - Only use async for extremely high volumes

3. **Complete Rollback:**
   - Deactivate new Integration Procedure elements
   - Restore original `SetRecordPSVQC` configuration
   - All processing returns to synchronous mode

---

## Future Enhancements

1. **User Selection of Practice Locations:**
   - Add checkbox to OmniScript step
   - Allow users to select which locations to process
   - Only process selected locations

2. **Filtering by Service Area:**
   - Add state/county filters
   - Only process locations within IBX service area
   - Ignore out-of-region locations

3. **Real-time Status Updates:**
   - Platform event to notify when processing completes
   - Email notification to case owner
   - Auto-refresh UI when status changes

4. **Practice Location Staging:**
   - Store locations in custom staging object
   - Allow review before final creation
   - Bulk approve/reject functionality
