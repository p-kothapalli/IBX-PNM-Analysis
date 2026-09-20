# PRM_FailedRecordStaging__c — Reusable Failed Record Framework
## Complete Object Specification

**Purpose:** Generic staging object for capturing failed DML operations from any batch/async process (Practitioner Creation, Practice Location Network creation, Taxonomy creation, etc.)

**Design Principle:** Process-agnostic — supports ANY target object type, ANY source process, deterministic replay capability

---

## Object Metadata

| Property | Value |
|----------|-------|
| **API Name** | `PRM_FailedRecordStaging__c` |
| **Label (Singular)** | Failed Record Staging |
| **Label (Plural)** | Failed Record Staging |
| **Record Name** | Auto Number: `FST-{00000}` |
| **Deployment Status** | Deployed |
| **Search Status** | Allow Search |
| **Allow Reports** | Yes |
| **Allow Activities** | Yes |
| **Track Field History** | Yes (recommended fields: PRM_Status__c, PRM_RetryCount__c, PRM_ErrorMessage__c) |
| **Object Sharing** | Public Read/Write |

---

## Field Specifications

### 1. Record Identification

#### **Name (Auto-Number)**
| Property | Value |
|----------|-------|
| **API Name** | `Name` |
| **Label** | Failed Record ID |
| **Type** | Auto Number |
| **Display Format** | `FST-{00000}` |
| **Starting Number** | 1 |
| **Description** | Unique identifier for staging record |
| **Help Text** | System-generated ID for tracking failed record |

---

### 2. Status & Lifecycle Fields

#### **PRM_Status__c** (REQUIRED)
| Property | Value |
|----------|-------|
| **API Name** | `PRM_Status__c` |
| **Label** | Status |
| **Type** | Picklist |
| **Required** | Yes |
| **Default Value** | `Pending` |
| **Picklist Values** | See table below |
| **Field-Level Security** | Visible to all, Editable by: System Admin, Operations Manager, Data Quality Analyst |
| **Description** | Lifecycle status of the staging record |
| **Help Text** | Tracks the current state of this failed record: Pending (awaiting fix) → Fixed (ready for retry) → Retried (successfully processed) or Failed - Terminal (requires manual intervention) |

**Picklist Values:**

| Value | API Name | Description | Set as Default | Color |
|-------|----------|-------------|----------------|-------|
| Pending | `Pending` | Failed record awaiting data correction or review | ✅ Yes | 🟡 Yellow |
| Under Review | `Under_Review` | Operations team reviewing error and correcting data | No | 🔵 Blue |
| Fixed | `Fixed` | Data corrected, ready for automated retry | No | 🟢 Green |
| Retried | `Retried` | Successfully retried and record created | No | 🟢 Green |
| Failed - Terminal | `Failed_Terminal` | Exceeded retry limit (3+), requires manual intervention | No | 🔴 Red |
| Archived | `Archived` | Resolved and archived for historical reference | No | ⚪ Gray |
| Cancelled | `Cancelled` | Retry cancelled by user (record no longer needed) | No | ⚪ Gray |

---

#### **PRM_RetryCount__c**
| Property | Value |
|----------|-------|
| **API Name** | `PRM_RetryCount__c` |
| **Label** | Retry Count |
| **Type** | Number(2, 0) |
| **Required** | No |
| **Default Value** | 0 |
| **Min Value** | 0 |
| **Max Value** | 99 |
| **Description** | Number of retry attempts for this record |
| **Help Text** | Automatically incremented each time retry is attempted. Terminal status at 3 retries. |

---

#### **PRM_NextRetryDate__c**
| Property | Value |
|----------|-------|
| **API Name** | `PRM_NextRetryDate__c` |
| **Label** | Next Retry Date |
| **Type** | DateTime |
| **Required** | No |
| **Description** | Scheduled date/time for next automated retry attempt |
| **Help Text** | Set by retry scheduler. Leave blank for immediate retry. |

---

#### **PRM_LastRetryDate__c**
| Property | Value |
|----------|-------|
| **API Name** | `PRM_LastRetryDate__c` |
| **Label** | Last Retry Date |
| **Type** | DateTime |
| **Required** | No |
| **Description** | Timestamp of last retry attempt |
| **Help Text** | Automatically updated when retry is executed |

---

#### **PRM_ResolvedDate__c**
| Property | Value |
|----------|-------|
| **API Name** | `PRM_ResolvedDate__c` |
| **Label** | Resolved Date |
| **Type** | DateTime |
| **Required** | No |
| **Description** | Timestamp when record was successfully retried or archived |
| **Help Text** | Automatically populated when Status = Retried or Archived |

---

#### **PRM_ResolvedBy__c**
| Property | Value |
|----------|-------|
| **API Name** | `PRM_ResolvedBy__c` |
| **Label** | Resolved By |
| **Type** | Lookup(User) |
| **Required** | No |
| **Delete Constraint** | Clear the value of this field |
| **Description** | User who resolved the staging record (manual retry or fixed data) |
| **Help Text** | Automatically populated when Status changes to Fixed or Retried |

---

### 3. Target Object & Payload Fields

#### **PRM_TargetObject__c** (REQUIRED)
| Property | Value |
|----------|-------|
| **API Name** | `PRM_TargetObject__c` |
| **Label** | Target Object |
| **Type** | Text(255) |
| **Required** | Yes |
| **Unique** | No |
| **External ID** | No |
| **Description** | API name of the target Salesforce object this record was attempting to create |
| **Help Text** | Examples: HealthcarePlanNetwork, HealthcarePractitionerFacility, PracticeLocationNetwork__c, TaxonomyAssignment__c |

---

#### **PRM_TargetObjectLabel__c** (Formula - Display Only)
| Property | Value |
|----------|-------|
| **API Name** | `PRM_TargetObjectLabel__c` |
| **Label** | Target Object Label |
| **Type** | Formula(Text) |
| **Formula** | See below |
| **Description** | User-friendly label for target object (for display in list views) |

**Formula:**
```apex
CASE(PRM_TargetObject__c,
  "HealthcarePlanNetwork", "Healthcare Plan Network",
  "HealthcarePractitionerFacility", "Healthcare Practitioner Facility",
  "PracticeLocationNetwork__c", "Practice Location Network",
  "PracticeLocationTaxonomy__c", "Practice Location Taxonomy",
  "TaxonomyNetworkAssignment__c", "Taxonomy Network Assignment",
  "PayerNetworkAssignment__c", "Payer Network Assignment",
  "IFCCodeAssignment__c", "IFC Code Assignment",
  "ProviderFeature__c", "Provider Feature",
  "AffirmingCareCategory__c", "Affirming Care Category",
  "ProviderFeatureAssistiveAid__c", "Provider Feature Assistive Aid",
  "InfoCodeAssignment__c", "Info Code Assignment",
  PRM_TargetObject__c
)
```

---

#### **PRM_Payload__c** (REQUIRED)
| Property | Value |
|----------|-------|
| **API Name** | `PRM_Payload__c` |
| **Label** | Record Payload (JSON) |
| **Type** | Long Text Area(131,072) |
| **Visible Lines** | 10 |
| **Required** | Yes |
| **Description** | JSON serialization of the failed record (full sObject) |
| **Help Text** | Complete JSON representation of the record that failed to insert. Used for deterministic replay during retry. DO NOT manually edit unless you understand JSON structure. |

**Example Payload:**
```json
{
  "attributes": {
    "type": "HealthcarePlanNetwork"
  },
  "Name": "Blue Cross PPO - Main Street Clinic",
  "HealthcarePlanNetworkId": "0hX5e000000ABC123",
  "HealthcareFacilityId": "0hF5e000000DEF456",
  "EffectiveFrom": "2026-01-01",
  "EffectiveTo": "2026-12-31",
  "NetworkStatus__c": "Active",
  "IsPrimaryNetwork__c": true
}
```

---

#### **PRM_PayloadSize__c** (Formula - Monitoring)
| Property | Value |
|----------|-------|
| **API Name** | `PRM_PayloadSize__c` |
| **Label** | Payload Size (KB) |
| **Type** | Formula(Number) |
| **Decimal Places** | 2 |
| **Formula** | `LEN(PRM_Payload__c) / 1024` |
| **Description** | Size of payload in kilobytes (for monitoring large payloads) |

---

#### **PRM_RecordCount__c**
| Property | Value |
|----------|-------|
| **API Name** | `PRM_RecordCount__c` |
| **Label** | Record Count |
| **Type** | Number(3, 0) |
| **Required** | No |
| **Default Value** | 1 |
| **Description** | Number of records in this staging entry (1 for single record, >1 for batch payload) |
| **Help Text** | Most staging records represent 1 failed record. Bulk failures may batch multiple records in single payload. |

---

### 4. Error & Exception Fields

#### **PRM_ErrorMessage__c** (REQUIRED)
| Property | Value |
|----------|-------|
| **API Name** | `PRM_ErrorMessage__c` |
| **Label** | Error Message |
| **Type** | Text(255) |
| **Required** | Yes |
| **Description** | Primary error message from Database.SaveResult or Exception |
| **Help Text** | User-facing error message describing why the record failed. Truncated to 255 chars; see Exception Log for full stack trace. |

---

#### **PRM_ErrorMessageFull__c**
| Property | Value |
|----------|-------|
| **API Name** | `PRM_ErrorMessageFull__c` |
| **Label** | Full Error Message |
| **Type** | Long Text Area(32,768) |
| **Visible Lines** | 5 |
| **Required** | No |
| **Description** | Full untruncated error message (if > 255 chars) |
| **Help Text** | Complete error message including all validation errors, field-level errors, and stack trace if available |

---

#### **PRM_FailureType__c**
| Property | Value |
|----------|-------|
| **API Name** | `PRM_FailureType__c` |
| **Label** | Failure Type |
| **Type** | Picklist |
| **Required** | No |
| **Picklist Values** | See table below |
| **Description** | Classification of failure type for routing and reporting |
| **Help Text** | Automatically classified based on error message pattern. Used for case routing and error analytics. |

**Picklist Values:**

| Value | API Name | Description | Routing Target |
|-------|----------|-------------|----------------|
| Validation Error | `Validation` | Required field missing, invalid picklist value, field validation rule failure | Data Quality Queue |
| Missing Reference | `Missing_Reference` | Lookup field references non-existent record (e.g., invalid HealthcarePlanNetworkId) | Data Quality Queue |
| Duplicate Record | `Duplicate` | Unique constraint violation, duplicate external ID | Operations Queue |
| Field Length Exceeded | `Field_Length` | Text value exceeds field length (e.g., 255 char limit) | Data Quality Queue |
| UNABLE_TO_LOCK_ROW | `Lock_Row` | Record locking/contention issue (transient error) | Automated Retry (no queue) |
| FIELD_CUSTOM_VALIDATION_EXCEPTION | `Custom_Validation` | Custom validation rule failure | Data Quality Queue |
| REQUIRED_FIELD_MISSING | `Required_Field` | Required field is null or blank | Data Quality Queue |
| INVALID_FIELD_FOR_INSERT_UPDATE | `Invalid_Field` | Field doesn't exist or not accessible | Technical Support Queue |
| INSUFFICIENT_ACCESS_OR_READONLY | `Permissions` | User lacks CRUD/FLS permissions | Technical Support Queue |
| Other | `Other` | Uncategorized error | Operations Queue |

---

#### **PRM_StatusCode__c**
| Property | Value |
|----------|-------|
| **API Name** | `PRM_StatusCode__c` |
| **Label** | Status Code |
| **Type** | Text(100) |
| **Required** | No |
| **Description** | Salesforce error status code (e.g., FIELD_CUSTOM_VALIDATION_EXCEPTION) |
| **Help Text** | Raw Salesforce error code from Database.SaveResult.getErrors()[0].getStatusCode() |

---

#### **PRM_FieldName__c**
| Property | Value |
|----------|-------|
| **API Name** | `PRM_FieldName__c` |
| **Label** | Failed Field Name |
| **Type** | Text(255) |
| **Required** | No |
| **Description** | API name of the field that caused the error (if field-specific) |
| **Help Text** | Examples: HealthcarePlanNetworkId, EffectiveFrom, Name. Blank if error is record-level. |

---

#### **PRM_SeverityLevel__c**
| Property | Value |
|----------|-------|
| **API Name** | `PRM_SeverityLevel__c` |
| **Label** | Severity Level |
| **Type** | Picklist |
| **Required** | No |
| **Default Value** | `Error` |
| **Picklist Values** | `Warning`, `Error`, `Critical` |
| **Description** | Severity of the failure for prioritization |
| **Help Text** | Critical = impacts business operations; Error = standard failure; Warning = non-blocking issue |

---

### 5. Process Context Fields

#### **PRM_SourceProcess__c** (REQUIRED)
| Property | Value |
|----------|-------|
| **API Name** | `PRM_SourceProcess__c` |
| **Label** | Source Process |
| **Type** | Text(255) |
| **Required** | Yes |
| **Description** | Name of the process/flow that attempted to create the record |
| **Help Text** | Examples: PRM_CreateDelegatedHFNRecords, PRM_PracticeLocationNetworkBatch, PRM_TaxonomyAssignmentBatch |

---

#### **PRM_SourceProcessType__c**
| Property | Value |
|----------|-------|
| **API Name** | `PRM_SourceProcessType__c` |
| **Label** | Source Process Type |
| **Type** | Picklist |
| **Required** | No |
| **Picklist Values** | `Integration Procedure`, `Batch Apex`, `Queueable Apex`, `Flow`, `Process Builder`, `Trigger`, `Scheduled Job`, `Manual (Quick Action)` |
| **Description** | Type of automation that created the staging record |

---

#### **PRM_BatchJobId__c**
| Property | Value |
|----------|-------|
| **API Name** | `PRM_BatchJobId__c` |
| **Label** | Batch Job ID |
| **Type** | Text(18) |
| **Required** | No |
| **Description** | AsyncApexJob ID (for Batch/Queueable) or Flow Interview GUID |
| **Help Text** | Allows lookup of the exact batch execution that created this staging record. Used for debugging and audit trail. |

---

#### **PRM_TransactionId__c**
| Property | Value |
|----------|-------|
| **API Name** | `PRM_TransactionId__c` |
| **Label** | Transaction ID |
| **Type** | Text(36) |
| **Required** | No |
| **Description** | Unique ID grouping all staging records from same transaction/batch scope |
| **Help Text** | All records that failed in the same batch scope share this ID. Use to replay entire transaction together. |

---

#### **PRM_ExecutionContext__c**
| Property | Value |
|----------|-------|
| **API Name** | `PRM_ExecutionContext__c` |
| **Label** | Execution Context (JSON) |
| **Type** | Long Text Area(32,768) |
| **Visible Lines** | 5 |
| **Required** | No |
| **Description** | JSON of additional execution context (user, timestamp, input parameters, debug info) |
| **Help Text** | Debugging information: user ID, trigger context, input map, platform info |

**Example Execution Context:**
```json
{
  "userId": "0055e000000ABCD",
  "userName": "system.admin@ibx.com",
  "executionTime": "2026-04-22T14:35:00Z",
  "governorLimits": {
    "soqlQueries": 45,
    "dmlStatements": 8,
    "cpuTime": 12500
  },
  "inputParameters": {
    "caseManagerId": "0iT5e000000XYZ",
    "practitionerId": "0035e000000ABC"
  }
}
```

---

### 6. Parent Record Context Fields

#### **PRM_ParentRecordId__c** (REQUIRED)
| Property | Value |
|----------|-------|
| **API Name** | `PRM_ParentRecordId__c` |
| **Label** | Parent Record ID |
| **Type** | Text(18) |
| **Required** | Yes |
| **Description** | Salesforce ID of the parent/context record (e.g., CaseManager, IndividualApplication, Account) |
| **Help Text** | The "anchor" record this failed record belongs to. Used to group all failures for a single parent record. |

---

#### **PRM_ParentRecordObject__c**
| Property | Value |
|----------|-------|
| **API Name** | `PRM_ParentRecordObject__c` |
| **Label** | Parent Record Object |
| **Type** | Text(255) |
| **Required** | No |
| **Description** | API name of parent record's object type |
| **Help Text** | Examples: IndividualApplication, Account, Contract, HealthcareFacility |

---

#### **PRM_ParentRecordName__c** (Formula)
| Property | Value |
|----------|-------|
| **API Name** | `PRM_ParentRecordName__c` |
| **Label** | Parent Record Name |
| **Type** | Formula(Text) |
| **Formula** | `HYPERLINK("/" & PRM_ParentRecordId__c, PRM_ParentRecordId__c, "_blank")` |
| **Description** | Clickable link to parent record |

---

#### **PRM_CaseManager__c** (Lookup - Specific to Practitioner Flow)
| Property | Value |
|----------|-------|
| **API Name** | `PRM_CaseManager__c` |
| **Label** | Case Manager |
| **Type** | Lookup(IndividualApplication) |
| **Required** | No |
| **Delete Constraint** | Clear the value of this field (Set Null) |
| **Description** | Lookup to Case Manager (IndividualApplication) for practitioner-related failures |
| **Help Text** | Only populated for practitioner creation flows. Other processes use PRM_ParentRecordId__c. |

---

### 7. Relationship to Exception Log

#### **PRM_ExceptionLog__c**
| Property | Value |
|----------|-------|
| **API Name** | `PRM_ExceptionLog__c` |
| **Label** | Exception Log |
| **Type** | Lookup(PRM_ExceptionLog__c) |
| **Required** | No |
| **Delete Constraint** | Clear the value of this field (Set Null) |
| **Description** | Link to detailed exception log record (stack trace, full error details) |
| **Help Text** | Exception logs contain technical debugging info. Staging records contain business-recoverable data. |

---

### 8. Monitoring & Reporting Fields

#### **PRM_ProcessingDuration__c**
| Property | Value |
|----------|-------|
| **API Name** | `PRM_ProcessingDuration__c` |
| **Label** | Processing Duration (ms) |
| **Type** | Number(10, 0) |
| **Required** | No |
| **Description** | Time taken (in milliseconds) by the failed DML operation |
| **Help Text** | For performance monitoring. Captured from System.currentTimeMillis() before/after DML. |

---

#### **PRM_AgeInDays__c** (Formula)
| Property | Value |
|----------|-------|
| **API Name** | `PRM_AgeInDays__c` |
| **Label** | Age (Days) |
| **Type** | Formula(Number) |
| **Decimal Places** | 1 |
| **Formula** | `TODAY() - DATEVALUE(CreatedDate)` |
| **Description** | Number of days since staging record was created |

---

#### **PRM_IsStale__c** (Formula)
| Property | Value |
|----------|-------|
| **API Name** | `PRM_IsStale__c` |
| **Label** | Is Stale (>7 Days) |
| **Type** | Formula(Checkbox) |
| **Formula** | `PRM_AgeInDays__c > 7 && TEXT(PRM_Status__c) = "Pending"` |
| **Description** | Indicates aging staging records that need attention |

---

#### **PRM_Priority__c**
| Property | Value |
|----------|-------|
| **API Name** | `PRM_Priority__c` |
| **Label** | Priority |
| **Type** | Picklist |
| **Required** | No |
| **Default Value** | `Medium` |
| **Picklist Values** | `Low`, `Medium`, `High`, `Critical` |
| **Description** | Business priority for resolving this failure |
| **Help Text** | Set by Operations team or automatically based on SeverityLevel + AgeInDays |

---

#### **PRM_ResolutionNotes__c**
| Property | Value |
|----------|-------|
| **API Name** | `PRM_ResolutionNotes__c` |
| **Label** | Resolution Notes |
| **Type** | Long Text Area(32,768) |
| **Visible Lines** | 5 |
| **Required** | No |
| **Description** | Notes entered by Operations user documenting how the issue was resolved |
| **Help Text** | Examples: "Created missing payer network master record", "Corrected taxonomy code from 123X to 123N", "Marked as duplicate - existing record ID: xyz" |

---

### 9. Automation Helper Fields

#### **PRM_IsRetryEligible__c** (Formula)
| Property | Value |
|----------|-------|
| **API Name** | `PRM_IsRetryEligible__c` |
| **Label** | Is Retry Eligible |
| **Type** | Formula(Checkbox) |
| **Formula** | `AND(OR(TEXT(PRM_Status__c) = "Fixed", TEXT(PRM_Status__c) = "Pending"), PRM_RetryCount__c < 3, NOT(ISPICKVAL(PRM_FailureType__c, "Permissions")))` |
| **Description** | Indicates if this record can be automatically retried |

---

#### **PRM_AutoRetryEnabled__c**
| Property | Value |
|----------|-------|
| **API Name** | `PRM_AutoRetryEnabled__c` |
| **Label** | Enable Auto-Retry |
| **Type** | Checkbox |
| **Required** | No |
| **Default Value** | Checked (true) |
| **Description** | Allow automated retry batch to process this record |
| **Help Text** | Uncheck to exclude from automated retry (manual retry only) |

---

#### **PRM_RetryStrategy__c**
| Property | Value |
|----------|-------|
| **API Name** | `PRM_RetryStrategy__c` |
| **Label** | Retry Strategy |
| **Type** | Picklist |
| **Required** | No |
| **Default Value** | `Standard` |
| **Picklist Values** | `Standard`, `Immediate`, `Deferred`, `Manual Only` |
| **Description** | Controls when and how retry is attempted |
| **Help Text** | Standard = daily batch at 2 AM; Immediate = retry in next 5 min; Deferred = wait until NextRetryDate; Manual Only = requires Quick Action |

---

### 10. Audit & Compliance Fields

#### **PRM_CreatedByProcess__c** (Auto-populated via default value)
| Property | Value |
|----------|-------|
| **API Name** | `PRM_CreatedByProcess__c` |
| **Label** | Created By Process |
| **Type** | Text(255) |
| **Required** | No |
| **Default Value** | `$User.Name` |
| **Description** | User or system process that created this staging record |

---

#### **PRM_DataSensitivityLevel__c**
| Property | Value |
|----------|-------|
| **API Name** | `PRM_DataSensitivityLevel__c` |
| **Label** | Data Sensitivity Level |
| **Type** | Picklist |
| **Required** | No |
| **Default Value** | `Internal` |
| **Picklist Values** | `Public`, `Internal`, `Confidential`, `Restricted (PHI/PII)` |
| **Description** | Sensitivity classification for payload data (for compliance/HIPAA) |
| **Help Text** | If payload contains PHI/PII, mark as Restricted. Governs who can view/edit staging record. |

---

## Validation Rules

### VR-001: Retry Count Cannot Decrease
| Property | Value |
|----------|-------|
| **API Name** | `VR_RetryCount_CannotDecrease` |
| **Error Condition Formula** | `AND(NOT(ISNEW()), PRM_RetryCount__c < PRIORVALUE(PRM_RetryCount__c))` |
| **Error Message** | "Retry Count cannot be manually decreased. Current: {PRM_RetryCount__c}, Previous: {PRIORVALUE(PRM_RetryCount__c)}" |
| **Error Location** | `PRM_RetryCount__c` field |
| **Active** | Yes |

---

### VR-002: Terminal Status Requires 3+ Retries
| Property | Value |
|----------|-------|
| **API Name** | `VR_Terminal_RequiresRetries` |
| **Error Condition Formula** | `AND(TEXT(PRM_Status__c) = "Failed_Terminal", PRM_RetryCount__c < 3)` |
| **Error Message** | "Cannot set status to 'Failed - Terminal' until 3 retry attempts have been made. Current retry count: {PRM_RetryCount__c}" |
| **Error Location** | `PRM_Status__c` field |
| **Active** | Yes |

---

### VR-003: Retried Status Requires Resolved Date
| Property | Value |
|----------|-------|
| **API Name** | `VR_Retried_RequiresResolvedDate` |
| **Error Condition Formula** | `AND(TEXT(PRM_Status__c) = "Retried", ISBLANK(PRM_ResolvedDate__c))` |
| **Error Message** | "Resolved Date is required when Status = Retried" |
| **Error Location** | `PRM_ResolvedDate__c` field |
| **Active** | Yes |

---

### VR-004: Parent Record ID Must Be Valid Salesforce ID
| Property | Value |
|----------|-------|
| **API Name** | `VR_ParentRecordId_ValidFormat` |
| **Error Condition Formula** | `AND(NOT(ISBLANK(PRM_ParentRecordId__c)), LEN(PRM_ParentRecordId__c) != 15, LEN(PRM_ParentRecordId__c) != 18)` |
| **Error Message** | "Parent Record ID must be a valid 15 or 18-character Salesforce ID" |
| **Error Location** | `PRM_ParentRecordId__c` field |
| **Active** | Yes |

---

## Workflow Rules / Process Builder

### Auto-Populate: Resolved Date on Status Change
| Property | Value |
|----------|-------|
| **Trigger** | Record is updated |
| **Criteria** | `PRM_Status__c` changed to `Retried`, `Archived`, or `Cancelled` |
| **Action** | Field Update: `PRM_ResolvedDate__c = NOW()` |
| **Action** | Field Update: `PRM_ResolvedBy__c = $User.Id` |

---

### Auto-Populate: Failure Type from Error Message
| Property | Value |
|----------|-------|
| **Trigger** | Record is created or updated |
| **Criteria** | `PRM_FailureType__c` is blank AND `PRM_ErrorMessage__c` is not blank |
| **Action** | Call Apex Class: `PRM_FailureTypeClassifier.classifyError(stagingRecordId)` |

**Apex Logic (simplified):**
```apex
public class PRM_FailureTypeClassifier {
    public static void classifyError(Id stagingRecordId) {
        PRM_FailedRecordStaging__c record = [SELECT PRM_ErrorMessage__c, PRM_StatusCode__c FROM PRM_FailedRecordStaging__c WHERE Id = :stagingRecordId];
        
        if (record.PRM_ErrorMessage__c.contains('Required field') || record.PRM_StatusCode__c == 'REQUIRED_FIELD_MISSING') {
            record.PRM_FailureType__c = 'Required_Field';
        } else if (record.PRM_ErrorMessage__c.contains('invalid ID') || record.PRM_ErrorMessage__c.contains('doesn\'t exist')) {
            record.PRM_FailureType__c = 'Missing_Reference';
        } else if (record.PRM_StatusCode__c == 'DUPLICATE_VALUE') {
            record.PRM_FailureType__c = 'Duplicate';
        } else if (record.PRM_StatusCode__c == 'UNABLE_TO_LOCK_ROW') {
            record.PRM_FailureType__c = 'Lock_Row';
        } else if (record.PRM_StatusCode__c == 'FIELD_CUSTOM_VALIDATION_EXCEPTION') {
            record.PRM_FailureType__c = 'Custom_Validation';
        } else {
            record.PRM_FailureType__c = 'Other';
        }
        
        update record;
    }
}
```

---

## Page Layouts

### Standard Layout: "Failed Record Staging Layout"

#### Section 1: Key Information (2 columns, Always Expanded)
- **Column 1:**
  - Failed Record ID (Name) — Read Only
  - Status — Editable by Operations
  - Priority — Editable
  - Target Object — Read Only
  - Target Object Label (Formula) — Read Only
  
- **Column 2:**
  - Failure Type — Read Only (auto-classified)
  - Severity Level — Editable
  - Retry Count — Read Only
  - Age (Days) — Formula, Read Only
  - Is Stale (>7 Days) — Formula, Read Only

---

#### Section 2: Error Details (2 columns, Always Expanded)
- **Column 1:**
  - Error Message — Read Only
  - Status Code — Read Only
  - Failed Field Name — Read Only
  
- **Column 2:**
  - Exception Log (Lookup) — Read Only
  - Full Error Message — Read Only

---

#### Section 3: Record Payload (1 column, Collapsed by Default)
- Record Payload (JSON) — Read Only for most users, Editable for System Admin only
- Payload Size (KB) — Formula, Read Only
- Record Count — Read Only

---

#### Section 4: Retry Management (2 columns, Always Expanded)
- **Column 1:**
  - Enable Auto-Retry — Editable
  - Retry Strategy — Editable
  - Next Retry Date — Editable
  
- **Column 2:**
  - Last Retry Date — Read Only
  - Resolved Date — Read Only
  - Resolved By (Lookup to User) — Read Only

---

#### Section 5: Process Context (2 columns, Collapsed by Default)
- **Column 1:**
  - Source Process — Read Only
  - Source Process Type — Read Only
  - Batch Job ID — Read Only
  
- **Column 2:**
  - Transaction ID — Read Only
  - Created By Process — Read Only
  - Processing Duration (ms) — Read Only

---

#### Section 6: Parent Record Context (2 columns, Always Expanded)
- **Column 1:**
  - Parent Record ID — Read Only
  - Parent Record Object — Read Only
  - Parent Record Name (Hyperlink Formula) — Read Only
  
- **Column 2:**
  - Case Manager (Lookup) — Read Only (specific to practitioner flow)

---

#### Section 7: Resolution & Notes (1 column, Always Expanded)
- Resolution Notes — Editable (Long Text Area)

---

#### Section 8: System Information (2 columns, Collapsed by Default)
- **Column 1:**
  - Created By — Read Only
  - Created Date — Read Only
  
- **Column 2:**
  - Last Modified By — Read Only
  - Last Modified Date — Read Only

---

### Related Lists (in order):
1. **Exception Logs** (if PRM_ExceptionLog__c is populated)
2. **Activities** (Tasks/Events related to this staging record)
3. **Notes & Attachments**
4. **Field History** (if Field History Tracking enabled)

---

## List Views

### 1. All Failed Records
| Property | Value |
|----------|-------|
| **API Name** | `All_Failed_Records` |
| **Filter** | (none - all records) |
| **Columns** | Name, Status, Target Object Label, Parent Record Name, Error Message, Age (Days), Created Date, Owner |
| **Sort** | Created Date (descending) |
| **Access** | All Users |

---

### 2. Pending - Awaiting Fix
| Property | Value |
|----------|-------|
| **API Name** | `Pending_Awaiting_Fix` |
| **Filter** | `Status = "Pending"` |
| **Columns** | Name, Priority, Target Object Label, Parent Record Name, Error Message, Age (Days), Is Stale, Owner |
| **Sort** | Priority (High → Low), then Age (Days, descending) |
| **Access** | All Users |

---

### 3. Fixed - Ready for Retry
| Property | Value |
|----------|-------|
| **API Name** | `Fixed_Ready_for_Retry` |
| **Filter** | `Status = "Fixed"` AND `Is Retry Eligible = TRUE` |
| **Columns** | Name, Target Object Label, Parent Record Name, Retry Count, Next Retry Date, Owner |
| **Sort** | Next Retry Date (ascending) |
| **Access** | All Users |

---

### 4. Stale Records (> 7 Days)
| Property | Value |
|----------|-------|
| **API Name** | `Stale_Records_7Days` |
| **Filter** | `Is Stale (>7 Days) = TRUE` AND `Status = "Pending"` |
| **Columns** | Name, Priority, Target Object Label, Parent Record Name, Error Message, Age (Days), Owner |
| **Sort** | Age (Days, descending) |
| **Access** | Managers, Operations Team |

---

### 5. Terminal Failures - Manual Review Required
| Property | Value |
|----------|-------|
| **API Name** | `Terminal_Failures` |
| **Filter** | `Status = "Failed - Terminal"` |
| **Columns** | Name, Severity Level, Target Object Label, Parent Record Name, Error Message, Retry Count, Owner |
| **Sort** | Severity Level (Critical → Low), then Created Date (descending) |
| **Access** | Managers, Data Quality Analysts |

---

### 6. Data Quality Issues
| Property | Value |
|----------|-------|
| **API Name** | `Data_Quality_Issues` |
| **Filter** | `Failure Type` IN (`Validation`, `Required_Field`, `Missing_Reference`, `Field_Length`) AND `Status` IN (`Pending`, `Under Review`) |
| **Columns** | Name, Failure Type, Target Object Label, Failed Field Name, Error Message, Age (Days), Owner |
| **Sort** | Created Date (descending) |
| **Access** | Data Quality Analysts, Operations Team |

---

### 7. Recently Resolved (Last 30 Days)
| Property | Value |
|----------|-------|
| **API Name** | `Recently_Resolved_30Days` |
| **Filter** | `Status` IN (`Retried`, `Archived`) AND `Resolved Date = LAST_N_DAYS:30` |
| **Columns** | Name, Status, Target Object Label, Resolved Date, Resolved By, Resolution Notes |
| **Sort** | Resolved Date (descending) |
| **Access** | All Users |

---

### 8. My Failed Records
| Property | Value |
|----------|-------|
| **API Name** | `My_Failed_Records` |
| **Filter** | `Owner = $User.Id` AND `Status` IN (`Pending`, `Under Review`, `Fixed`) |
| **Columns** | Name, Status, Priority, Target Object Label, Error Message, Age (Days) |
| **Sort** | Priority (High → Low), then Age (Days, descending) |
| **Access** | All Users |

---

### 9. Transient Errors (Lock Row)
| Property | Value |
|----------|-------|
| **API Name** | `Transient_Errors_Lock_Row` |
| **Filter** | `Failure Type = "Lock_Row"` AND `Status = "Pending"` |
| **Columns** | Name, Target Object Label, Parent Record Name, Retry Count, Next Retry Date |
| **Sort** | Next Retry Date (ascending) |
| **Access** | System Admins, Technical Support |

---

### 10. By Process - Practitioner Creation
| Property | Value |
|----------|-------|
| **API Name** | `Process_Practitioner_Creation` |
| **Filter** | `Source Process` CONTAINS (`PRM_CreateDelegatedHFNRecords`, `PRM_ExistingPrimaryPracticeLocationLogicDelg`, `PRM_PractitionerAddressCreation`) |
| **Columns** | Name, Status, Source Process, Case Manager, Error Message, Age (Days), Owner |
| **Sort** | Created Date (descending) |
| **Access** | All Users |

---

### 11. By Target Object - Network Records
| Property | Value |
|----------|-------|
| **API Name** | `Target_Network_Records` |
| **Filter** | `Target Object` IN (`HealthcarePlanNetwork`, `PracticeLocationNetwork__c`, `TaxonomyNetworkAssignment__c`) |
| **Columns** | Name, Status, Target Object Label, Parent Record Name, Error Message, Age (Days), Owner |
| **Sort** | Created Date (descending) |
| **Access** | All Users |

---

## Quick Actions

### 1. Mark as Fixed
| Property | Value |
|----------|-------|
| **API Name** | `Mark_as_Fixed` |
| **Type** | Update Record |
| **Target** | Current Record |
| **Fields** | `PRM_Status__c = "Fixed"`, `PRM_ResolutionNotes__c` (user input) |
| **Success Message** | "Staging record marked as Fixed and ready for retry." |

---

### 2. Retry This Record
| Property | Value |
|----------|-------|
| **API Name** | `Retry_This_Record` |
| **Type** | Lightning Component (Custom) or Screen Flow |
| **Apex Class** | `PRM_RetryFailedProcessingController.retrySingleRecord(Id stagingRecordId)` |
| **Success Message** | "Retry initiated. Check status in 5-10 minutes." |

---

### 3. Cancel (Mark as No Longer Needed)
| Property | Value |
|----------|-------|
| **API Name** | `Cancel_Staging_Record` |
| **Type** | Update Record |
| **Target** | Current Record |
| **Fields** | `PRM_Status__c = "Cancelled"`, `PRM_ResolutionNotes__c` (user input) |
| **Success Message** | "Staging record cancelled." |

---

### 4. Escalate to Technical Support
| Property | Value |
|----------|-------|
| **API Name** | `Escalate_to_Support` |
| **Type** | Create Record (Case or Task) |
| **Target** | Create new Case, link to this staging record |
| **Pre-populated Fields** | Subject = "Failed Record Staging Issue - {Name}", Description = {Error Message}, Origin = "Staging Queue" |

---

## Permission Sets

### Permission Set 1: PRM_FailedRecordStaging_OperationsUser
| Permission | Access Level |
|------------|--------------|
| **Object** | Read, Create, Edit |
| **Field-Level Security** | Read/Edit on all fields except: PRM_Payload__c (Read Only), PRM_RetryCount__c (Read Only) |
| **Record Types** | All |
| **Assigned To** | Operations Team, Credentialing Specialists |

---

### Permission Set 2: PRM_FailedRecordStaging_DataQualityAnalyst
| Permission | Access Level |
|------------|--------------|
| **Object** | Read, Create, Edit |
| **Field-Level Security** | Read/Edit on all fields including PRM_Payload__c (Edit) |
| **Record Types** | All |
| **Assigned To** | Data Quality Analysts |

---

### Permission Set 3: PRM_FailedRecordStaging_SystemAdmin
| Permission | Access Level |
|------------|--------------|
| **Object** | Read, Create, Edit, Delete |
| **Field-Level Security** | Full Edit on all fields |
| **Record Types** | All |
| **Assigned To** | System Administrators, Technical Support |

---

## Reports & Dashboards

### Report 1: Failed Record Aging Report
| Property | Value |
|----------|-------|
| **Report Type** | Failed Record Staging (Custom Report Type) |
| **Grouping** | Grouped by Status, then by Target Object |
| **Filters** | Status IN (Pending, Under Review, Fixed) |
| **Columns** | Name, Priority, Age (Days), Error Message, Owner |
| **Summary** | Count of Records, Average Age (Days) |
| **Chart Type** | Horizontal Bar (X-axis: Status, Y-axis: Record Count) |

---

### Report 2: Failure Type Breakdown
| Property | Value |
|----------|-------|
| **Report Type** | Failed Record Staging |
| **Grouping** | Grouped by Failure Type |
| **Filters** | Created Date = LAST_30_DAYS |
| **Columns** | Name, Target Object Label, Error Message, Created Date |
| **Summary** | Count of Records |
| **Chart Type** | Donut Chart (Failure Type distribution) |

---

### Report 3: Retry Success Rate
| Property | Value |
|----------|-------|
| **Report Type** | Failed Record Staging |
| **Grouping** | Grouped by Status |
| **Filters** | Resolved Date = LAST_30_DAYS |
| **Columns** | Name, Retry Count, Resolved Date, Source Process |
| **Summary** | Count of Records (Status = Retried) / Count of Records (All Statuses) = Success Rate % |
| **Chart Type** | Gauge Chart (0-100% success rate) |

---

### Dashboard: PRM Operations Staging Dashboard

**Component 1: Pending Failed Records by Priority (Gauge)**
- Metric: Count of records where Status = Pending, grouped by Priority
- Thresholds: Green (< 10), Yellow (10-50), Red (> 50)

**Component 2: Aging Report (Horizontal Bar)**
- Source: Report 1 (Failed Record Aging Report)

**Component 3: Failure Type Breakdown (Donut Chart)**
- Source: Report 2 (Failure Type Breakdown)

**Component 4: Retry Success Rate (Gauge)**
- Source: Report 3 (Retry Success Rate)
- Target: > 95% success rate

**Component 5: Top 10 Most Common Errors (Table)**
- Grouping: Error Message (top 10 by count)
- Columns: Error Message, Count, Failure Type

**Component 6: Stale Records Alert (Metric)**
- Metric: Count of records where Is Stale = TRUE
- Threshold: Red if > 20 records

---

## Integration with Other Objects

### Related List on IndividualApplication (Case Manager)

**Related List:** "Failed Record Staging"
- **Relationship Field:** `PRM_CaseManager__c`
- **Columns:** Name, Status, Target Object Label, Error Message, Age (Days), Owner
- **Sort:** Created Date (descending)
- **Buttons:** "Retry All Pending", "View All Failed Records"

---

### Related List on PRM_ExceptionLog__c

**Related List:** "Failed Record Staging"
- **Relationship Field:** `PRM_ExceptionLog__c`
- **Columns:** Name, Status, Target Object Label, Payload Size (KB), Retry Count
- **Sort:** Created Date (descending)

---

## Data Archival Strategy

### Automated Archival (Scheduled Apex)

**Schedule:** Weekly (Sunday at 2 AM)

**Criteria for Archival:**
- Status = "Retried" AND Resolved Date > 90 days ago
- Status = "Cancelled" AND Last Modified Date > 90 days ago
- Status = "Archived"

**Action:**
1. Export to external archive (S3, data warehouse)
2. Delete from Salesforce (or move to Big Object)

**Apex Class:** `PRM_FailedRecordStagingArchivalBatch`

---

## Usage Examples

### Example 1: Practitioner Creation - Failed Network Record

```apex
// In PRM_CreateDelegatedHFNRecords IP
List<HealthcarePlanNetwork> networksToInsert = new List<HealthcarePlanNetwork>();
// ... populate networks ...

Database.SaveResult[] results = Database.insert(networksToInsert, false);

List<PRM_FailedRecordStaging__c> stagingRecords = new List<PRM_FailedRecordStaging__c>();

for (Integer i = 0; i < results.size(); i++) {
    if (!results[i].isSuccess()) {
        PRM_FailedRecordStaging__c staging = new PRM_FailedRecordStaging__c();
        staging.PRM_Status__c = 'Pending';
        staging.PRM_TargetObject__c = 'HealthcarePlanNetwork';
        staging.PRM_Payload__c = JSON.serialize(networksToInsert[i]);
        staging.PRM_ParentRecordId__c = caseManagerId;
        staging.PRM_ParentRecordObject__c = 'IndividualApplication';
        staging.PRM_CaseManager__c = caseManagerId;
        staging.PRM_ErrorMessage__c = results[i].getErrors()[0].getMessage();
        staging.PRM_StatusCode__c = String.valueOf(results[i].getErrors()[0].getStatusCode());
        staging.PRM_FieldName__c = String.valueOf(results[i].getErrors()[0].getFields()[0]);
        staging.PRM_SourceProcess__c = 'PRM_CreateDelegatedHFNRecords';
        staging.PRM_SourceProcessType__c = 'Integration Procedure';
        staging.PRM_BatchJobId__c = batchJobId;
        staging.PRM_TransactionId__c = transactionId;
        staging.PRM_SeverityLevel__c = 'Error';
        staging.PRM_RecordCount__c = 1;
        staging.PRM_ExceptionLog__c = exceptionLogId; // if exception log exists
        stagingRecords.add(staging);
    }
}

if (!stagingRecords.isEmpty()) {
    insert stagingRecords;
}
```

---

### Example 2: Practice Location Network Batch - Future Use

```apex
// In PRM_PracticeLocationNetworkBatch
global class PRM_PracticeLocationNetworkBatch implements Database.Batchable<SObject> {
    
    global void execute(Database.BatchableContext BC, List<PracticeLocation__c> scope) {
        List<PracticeLocationNetwork__c> networksToInsert = new List<PracticeLocationNetwork__c>();
        // ... build networks from practice locations ...
        
        Database.SaveResult[] results = Database.insert(networksToInsert, false);
        
        // Use same staging framework!
        List<PRM_FailedRecordStaging__c> stagingRecords = new List<PRM_FailedRecordStaging__c>();
        
        for (Integer i = 0; i < results.size(); i++) {
            if (!results[i].isSuccess()) {
                PRM_FailedRecordStaging__c staging = new PRM_FailedRecordStaging__c();
                staging.PRM_TargetObject__c = 'PracticeLocationNetwork__c';
                staging.PRM_Payload__c = JSON.serialize(networksToInsert[i]);
                staging.PRM_ParentRecordId__c = scope[i].Id; // Practice Location
                staging.PRM_ParentRecordObject__c = 'PracticeLocation__c';
                staging.PRM_ErrorMessage__c = results[i].getErrors()[0].getMessage();
                staging.PRM_SourceProcess__c = 'PRM_PracticeLocationNetworkBatch';
                staging.PRM_SourceProcessType__c = 'Batch Apex';
                staging.PRM_BatchJobId__c = String.valueOf(BC.getJobId());
                stagingRecords.add(staging);
            }
        }
        
        if (!stagingRecords.isEmpty()) {
            insert stagingRecords;
        }
    }
}
```

---

## Reusability Checklist

✅ **Process-Agnostic:** No hardcoded references to specific IPs or flows  
✅ **Object-Agnostic:** Supports any target object type via text field  
✅ **Payload-Agnostic:** JSON serialization supports any sObject structure  
✅ **Parent-Agnostic:** Generic ParentRecordId field (text) supports any parent object  
✅ **Error-Agnostic:** Classification logic works for any DML error type  
✅ **Retry-Ready:** Payload contains full record for deterministic replay  
✅ **Reporting-Ready:** Fields support cross-process analytics and dashboards  
✅ **Monitoring-Ready:** Aging, stale detection, priority work across all processes  
✅ **Audit-Compliant:** Full execution context captured for any process  
✅ **Permission-Flexible:** Permission sets support different team roles

---

## Summary

**Total Fields:** 42  
**Required Fields:** 6 (`Name`, `PRM_Status__c`, `PRM_TargetObject__c`, `PRM_Payload__c`, `PRM_ErrorMessage__c`, `PRM_ParentRecordId__c`, `PRM_SourceProcess__c`)  
**Formula Fields:** 5 (for display, monitoring, and eligibility checks)  
**Lookup Fields:** 3 (`PRM_CaseManager__c`, `PRM_ExceptionLog__c`, `PRM_ResolvedBy__c`)  
**Validation Rules:** 4  
**List Views:** 11  
**Quick Actions:** 4  
**Permission Sets:** 3  
**Reports:** 3  
**Dashboard Components:** 6  

**Reusability:** ✅ Fully reusable for any batch/async process creating any object type

---

**Document Version:** 1.0  
**Last Updated:** 2026-04-22  
**Next Review:** After first implementation (Practitioner Creation)
