# ReCred CAQH Batch Monitoring Dashboard

## Dashboard Purpose
This dashboard provides admins with SOQL queries to manually investigate failures in the `PRM_CheckCAQHAccessOnDueAccountsBatch` that creates reCred case managers.

---

## Section 1: Batch Job Status

### 1.1 - Check Last Batch Execution Status
```sql
SELECT Id, Status, JobType, MethodName, NumberOfErrors, 
       JobItemsProcessed, TotalJobItems, CreatedDate, CompletedDate,
       ExtendedStatus
FROM AsyncApexJob
WHERE ApexClass.Name = 'PRM_CheckCAQHAccessOnDueAccountsBatch'
ORDER BY CreatedDate DESC
LIMIT 10
```
**Purpose:** Shows the last 10 batch runs with status, errors, and completion details.

### 1.2 - Check Batch Errors
```sql
SELECT Id, AsyncApexJobId, Message, StackTrace, 
       ExtendedStatus, JobScope, NumberOfErrors
FROM ApexTestQueueItem
WHERE AsyncApexJobId IN 
  (SELECT Id FROM AsyncApexJob 
   WHERE ApexClass.Name = 'PRM_CheckCAQHAccessOnDueAccountsBatch'
   AND CreatedDate = TODAY)
```
**Purpose:** Shows specific error messages and stack traces from today's batch runs.

---

## Section 2: Accounts Due for Processing

### 2.1 - Accounts in Scope for Today's Batch
*Note: Replace the date values based on PRM_CAQHDateRangeSetting__c configuration*

```sql
SELECT Id, Name, PersonContactId, PRM_ReCredDueDate__c, 
       PRM_IsReCredDue__c, PRM_DelegatedOnly__c, PRM_PNC__c,
       RecordType.Name, IsActive
FROM Account
WHERE RecordTypeId = :pracRecTypeId
  AND IsActive = true
  AND PRM_DelegatedOnly__c = false
  AND PRM_PNC__c = false
  AND PRM_ReCredDueDate__c >= :startDate
  AND PRM_ReCredDueDate__c <= :endDate
ORDER BY PRM_ReCredDueDate__c
```
**Purpose:** Shows all practitioner accounts that should be processed by the batch.

**To get date range values, first run:**
```sql
SELECT Name, PRM_DueDays__c, PRM_StartDate__c, PRM_EndDate__c, PRM_BatchSize__c
FROM PRM_CAQHDateRangeSetting__c
WHERE Name = 'ReCredCAQHDateRange'
LIMIT 1
```

### 2.2 - Accounts Missing CAQH Identifiers
```sql
SELECT Id, Name, PersonContactId, PRM_ReCredDueDate__c
FROM Account
WHERE RecordTypeId IN (SELECT Id FROM RecordType 
                       WHERE DeveloperName = 'PRM_Practitioner' 
                       AND SObjectType = 'Account')
  AND IsActive = true
  AND PRM_DelegatedOnly__c = false
  AND PRM_PNC__c = false
  AND PRM_ReCredDueDate__c = NEXT_N_DAYS:180
  AND Id NOT IN (SELECT ParentRecordId FROM Identifier 
                 WHERE PRM_Type__c = 'CAQH')
ORDER BY PRM_ReCredDueDate__c
```
**Purpose:** Identifies accounts that will fail because they lack CAQH identifiers.

### 2.3 - Check CAQH Identifiers for Specific Account
*Replace {AccountId} with actual Account ID*

```sql
SELECT Id, IdValue, ParentRecordId, PRM_Type__c, 
       PRM_AttestationDate__c, PRM_Pending__c
FROM Identifier
WHERE ParentRecordId = '{AccountId}'
  AND PRM_Type__c = 'CAQH'
```
**Purpose:** Shows CAQH identifier details for troubleshooting a specific account.

---

## Section 3: Case Manager Creation Status

### 3.1 - Case Managers Created Today
```sql
SELECT Id, AccountId, Account.Name, ApplicationType, 
       PRM_Stage__c, Status, Category, PRM_CAQHAccessible__c,
       ApplicationCaseId, CreatedDate
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_ReCredentialing'
  AND CreatedDate = TODAY
ORDER BY CreatedDate DESC
```
**Purpose:** Shows all reCred case managers created today by the batch.

### 3.2 - Case Managers with Missing Case Links
```sql
SELECT Id, AccountId, Account.Name, ApplicationType, 
       PRM_Stage__c, Status, ApplicationCaseId, CreatedDate
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_ReCredentialing'
  AND CreatedDate = TODAY
  AND ApplicationCaseId = null
ORDER BY CreatedDate DESC
```
**Purpose:** Identifies case managers that weren't properly linked to cases (linkRecords failure).

### 3.3 - Cases Created Today Without Case Managers
```sql
SELECT Id, AccountId, Account.Name, Type, Status, 
       PRM_CaseManager__c, ContactId, CreatedDate
FROM Case
WHERE RecordType.DeveloperName = 'PRM_PRM'
  AND CreatedDate = TODAY
  AND PRM_CaseManager__c = null
ORDER BY CreatedDate DESC
```
**Purpose:** Identifies cases that weren't properly linked to case managers.

### 3.4 - Duplicate Case Managers Check
```sql
SELECT AccountId, Account.Name, COUNT(Id) CaseManagerCount
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_ReCredentialing'
  AND CreatedDate = TODAY
  AND Status IN ('Pending NPDB', 'Pending CAQH Access')
GROUP BY AccountId, Account.Name
HAVING COUNT(Id) > 1
ORDER BY COUNT(Id) DESC
```
**Purpose:** Identifies accounts with duplicate case managers created today.

---

## Section 4: Related Data Validation

### 4.1 - Accounts Missing Required Address Data
*Address is required for Adverse Action Log creation*

```sql
SELECT acc.Id, acc.Name, acc.PersonContactId, acc.PRM_ReCredDueDate__c,
       (SELECT COUNT() FROM Addresses WHERE ParentId = acc.Id) AddressCount
FROM Account acc
WHERE acc.RecordTypeId IN (SELECT Id FROM RecordType 
                           WHERE DeveloperName = 'PRM_Practitioner' 
                           AND SObjectType = 'Account')
  AND acc.IsActive = true
  AND acc.PRM_DelegatedOnly__c = false
  AND acc.PRM_PNC__c = false
  AND acc.PRM_ReCredDueDate__c = NEXT_N_DAYS:180
  AND acc.Id NOT IN (SELECT ParentId FROM Address WHERE ParentId != null)
```
**Purpose:** Identifies accounts that will fail Adverse Action Log creation due to missing addresses.

### 4.2 - Accounts Missing NPI Data
```sql
SELECT acc.Id, acc.Name, acc.PersonContactId, acc.PRM_ReCredDueDate__c
FROM Account acc
WHERE acc.RecordTypeId IN (SELECT Id FROM RecordType 
                           WHERE DeveloperName = 'PRM_Practitioner' 
                           AND SObjectType = 'Account')
  AND acc.IsActive = true
  AND acc.PRM_DelegatedOnly__c = false
  AND acc.PRM_PNC__c = false
  AND acc.PRM_ReCredDueDate__c = NEXT_N_DAYS:180
  AND acc.Id NOT IN (SELECT AccountId FROM HealthcareProviderNpi 
                     WHERE AccountId != null)
```
**Purpose:** Identifies accounts missing NPI records (required for Adverse Action Logs).

### 4.3 - Accounts Missing Business Licenses
```sql
SELECT acc.Id, acc.Name, acc.PersonContactId, acc.PRM_ReCredDueDate__c
FROM Account acc
WHERE acc.RecordTypeId IN (SELECT Id FROM RecordType 
                           WHERE DeveloperName = 'PRM_Practitioner' 
                           AND SObjectType = 'Account')
  AND acc.IsActive = true
  AND acc.PRM_DelegatedOnly__c = false
  AND acc.PRM_PNC__c = false
  AND acc.PRM_ReCredDueDate__c = NEXT_N_DAYS:180
  AND acc.PersonContactId NOT IN (SELECT ContactId FROM BusinessLicense 
                                  WHERE LicenseClass = 'SBRD')
```
**Purpose:** Identifies accounts missing business licenses (required for Adverse Action Logs).

### 4.4 - Accounts Missing Person Education
```sql
SELECT acc.Id, acc.Name, acc.PersonContactId, acc.PRM_ReCredDueDate__c
FROM Account acc
WHERE acc.RecordTypeId IN (SELECT Id FROM RecordType 
                           WHERE DeveloperName = 'PRM_Practitioner' 
                           AND SObjectType = 'Account')
  AND acc.IsActive = true
  AND acc.PRM_DelegatedOnly__c = false
  AND acc.PRM_PNC__c = false
  AND acc.PRM_ReCredDueDate__c = NEXT_N_DAYS:180
  AND acc.PersonContactId NOT IN (SELECT ContactId FROM PersonEducation)
```
**Purpose:** Identifies accounts missing education records (required for Adverse Action Logs).

---

## Section 5: Exception Logs

### 5.1 - Check Exception Logs for Batch
*Assumes PRM_ExceptionLogger creates records in a custom object*

```sql
SELECT Id, Name, PRM_ClassName__c, PRM_Message__c, PRM_StackTrace__c,
       PRM_LineNumber__c, PRM_RecordId__c, PRM_TypeName__c, 
       CreatedDate
FROM PRM_ExceptionLog__c
WHERE PRM_ClassName__c = 'PRM_CheckCAQHAccessOnDueAccountsBatch'
  AND CreatedDate = TODAY
ORDER BY CreatedDate DESC
```
**Purpose:** Shows all exceptions logged by the batch today.

### 5.2 - Exception Logs by Error Type
```sql
SELECT PRM_TypeName__c, COUNT(Id) ErrorCount, 
       PRM_Message__c
FROM PRM_ExceptionLog__c
WHERE PRM_ClassName__c = 'PRM_CheckCAQHAccessOnDueAccountsBatch'
  AND CreatedDate = TODAY
GROUP BY PRM_TypeName__c, PRM_Message__c
ORDER BY COUNT(Id) DESC
```
**Purpose:** Groups exceptions by type to identify common failure patterns.

### 5.3 - Missing Address Errors
```sql
SELECT Id, PRM_RecordId__c, PRM_Message__c, PRM_Description__c, 
       PRM_ExceptionDetails__c, CreatedDate
FROM PRM_ExceptionLog__c
WHERE PRM_ClassName__c = 'PRM_CheckCAQHAccessOnDueAccountsBatch'
  AND PRM_Message__c = 'Address is null'
  AND CreatedDate = TODAY
ORDER BY CreatedDate DESC
```
**Purpose:** Shows specific accounts that failed due to missing address data.

---

## Section 6: Adverse Action Logs

### 6.1 - Adverse Action Logs Created Today
```sql
SELECT Id, PRM_ProviderId__c, PRM_CaseManager__c, PRM_Status__c,
       PRM_IndividualNpi__c, PRM_OrganizationName__c, 
       PRM_PrimaryCity__c, PRM_PrimaryState__c, PRM_PrimaryZip__c,
       CreatedDate
FROM PRM_AdverseActionLog__c
WHERE RecordType.DeveloperName = 'PRM_Individual'
  AND CreatedDate = TODAY
ORDER BY CreatedDate DESC
```
**Purpose:** Shows all adverse action logs created by the batch today.

### 6.2 - Adverse Action Logs Not Linked to Case Managers
```sql
SELECT Id, PRM_ProviderId__c, PRM_CaseManager__c, PRM_Status__c,
       CreatedDate
FROM PRM_AdverseActionLog__c
WHERE RecordType.DeveloperName = 'PRM_Individual'
  AND CreatedDate = TODAY
  AND PRM_CaseManager__c = null
ORDER BY CreatedDate DESC
```
**Purpose:** Identifies adverse action logs that weren't linked to case managers.

---

## Section 7: Case Data Manager Status

### 7.1 - Case Data Managers Created Today
```sql
SELECT Id, PRM_CaseManager__c, PRM_CaseManager__r.Account.Name,
       CreatedDate
FROM PRM_CaseDataManager__c
WHERE CreatedDate = TODAY
ORDER BY CreatedDate DESC
```
**Purpose:** Shows all case data manager records created today.

### 7.2 - Check for Duplicate Case Data Managers
```sql
SELECT PRM_CaseManager__c, COUNT(Id) CDMCount
FROM PRM_CaseDataManager__c
WHERE CreatedDate = TODAY
  AND IsDeleted = false
GROUP BY PRM_CaseManager__c
HAVING COUNT(Id) > 1
```
**Purpose:** Identifies case managers with duplicate CDM records.

---

## Section 8: CAQH Validation Checks

### 8.1 - Accounts with CAQH Accessible = True (Created Today)
```sql
SELECT Id, AccountId, Account.Name, PRM_CAQHAccessible__c, 
       PRM_Stage__c, Status, CreatedDate
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_ReCredentialing'
  AND CreatedDate = TODAY
  AND PRM_CAQHAccessible__c = true
ORDER BY CreatedDate DESC
```
**Purpose:** Shows accounts that passed CAQH validation.

### 8.2 - Accounts with CAQH Accessible = False (Created Today)
```sql
SELECT Id, AccountId, Account.Name, PRM_CAQHAccessible__c, 
       PRM_Stage__c, Status, CreatedDate
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_ReCredentialing'
  AND CreatedDate = TODAY
  AND PRM_CAQHAccessible__c = false
ORDER BY CreatedDate DESC
```
**Purpose:** Shows accounts that failed CAQH validation (inactive/expired CAQH).

### 8.3 - CAQH Identifiers Updated Today
```sql
SELECT Id, ParentRecordId, IdValue, PRM_AttestationDate__c, 
       PRM_Pending__c, LastModifiedDate
FROM Identifier
WHERE PRM_Type__c = 'CAQH'
  AND LastModifiedDate = TODAY
ORDER BY LastModifiedDate DESC
```
**Purpose:** Shows CAQH identifiers that were updated with new attestation dates.

---

## Section 9: Existing RecredIA Check

### 9.1 - Accounts Skipped (Already Have Active Recred IA)
```sql
SELECT AccountId, Account.Name, COUNT(Id) RecredIACount
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_ReCredentialing'
  AND Status NOT IN ('Approved', 'Denied', 'Terminate')
  AND Account.PRM_ReCredDueDate__c = NEXT_N_DAYS:180
  AND Account.IsActive = true
  AND Account.PRM_DelegatedOnly__c = false
  AND Account.PRM_PNC__c = false
GROUP BY AccountId, Account.Name
HAVING COUNT(Id) > 1
```
**Purpose:** Identifies accounts that were skipped because they already have an active recred case manager.

---

## Section 10: Healthcare Provider Taxonomy (License Code)

### 10.1 - Check Provider Taxonomy Data for Account
*Replace {AccountId} with actual Account ID*

```sql
SELECT Id, AccountId, Account.Name, IsPrimaryTaxonomy,
       Taxonomy.Name, Taxonomy.PRM_NPDBLicensureCodeMD__c, 
       Taxonomy.PRM_NPDBLicensureCodeDO__c,
       PRM_ProviderType__r.Name, PRM_ProviderType__r.PRM_ProviderTypeCode__c
FROM HealthcareProviderTaxonomy
WHERE AccountId = '{AccountId}'
  AND IsPrimaryTaxonomy = true
```
**Purpose:** Shows the taxonomy data used to determine license code for Adverse Action Logs.

### 10.2 - Accounts Missing Primary Taxonomy
```sql
SELECT acc.Id, acc.Name, acc.PersonContactId, acc.PRM_ReCredDueDate__c
FROM Account acc
WHERE acc.RecordTypeId IN (SELECT Id FROM RecordType 
                           WHERE DeveloperName = 'PRM_Practitioner' 
                           AND SObjectType = 'Account')
  AND acc.IsActive = true
  AND acc.PRM_DelegatedOnly__c = false
  AND acc.PRM_PNC__c = false
  AND acc.PRM_ReCredDueDate__c = NEXT_N_DAYS:180
  AND acc.Id NOT IN (SELECT AccountId FROM HealthcareProviderTaxonomy 
                     WHERE IsPrimaryTaxonomy = true)
```
**Purpose:** Identifies accounts missing primary taxonomy (may use default license code '030').

---

## Section 11: Complete Data Readiness Report

### 11.1 - Account Readiness Summary
*This query helps identify accounts that may fail processing*

```sql
SELECT 
    acc.Id, 
    acc.Name, 
    acc.PRM_ReCredDueDate__c,
    (SELECT COUNT() FROM Identifiers WHERE PRM_Type__c = 'CAQH') AS CAQHCount,
    (SELECT COUNT() FROM Addresses) AS AddressCount,
    (SELECT COUNT() FROM HealthcareProviderNpis) AS NPICount,
    (SELECT COUNT() FROM Contacts WHERE Id = acc.PersonContactId 
     AND Id IN (SELECT ContactId FROM BusinessLicense WHERE LicenseClass = 'SBRD')) AS LicenseCount,
    (SELECT COUNT() FROM Contacts WHERE Id = acc.PersonContactId 
     AND Id IN (SELECT ContactId FROM PersonEducation)) AS EducationCount,
    (SELECT COUNT() FROM HealthcareProviderTaxonomies 
     WHERE IsPrimaryTaxonomy = true) AS TaxonomyCount
FROM Account acc
WHERE acc.RecordTypeId IN (SELECT Id FROM RecordType 
                           WHERE DeveloperName = 'PRM_Practitioner' 
                           AND SObjectType = 'Account')
  AND acc.IsActive = true
  AND acc.PRM_DelegatedOnly__c = false
  AND acc.PRM_PNC__c = false
  AND acc.PRM_ReCredDueDate__c = NEXT_N_DAYS:180
ORDER BY acc.PRM_ReCredDueDate__c
```
**Purpose:** Comprehensive readiness check showing which data is missing for each account.

**Interpretation:**
- **CAQHCount = 0**: Will fail immediately (no CAQH identifier)
- **AddressCount = 0**: Adverse Action Log creation will fail
- **NPICount = 0**: Adverse Action Log will have missing NPI data
- **LicenseCount = 0**: Adverse Action Log will have missing license data
- **EducationCount = 0**: Adverse Action Log will have missing education data
- **TaxonomyCount = 0**: Will use default license code '030'

---

## Section 12: Manual Troubleshooting Queries

### 12.1 - Check Complete Account Data for Specific Practitioner
*Replace {AccountId} with actual Account ID*

```sql
-- Account Details
SELECT Id, Name, PersonContactId, PersonBirthdate, 
       PRM_ReCredDueDate__c, PRM_IsReCredDue__c, 
       PRM_DelegatedOnly__c, PRM_PNC__c, IsActive,
       RecordType.Name
FROM Account
WHERE Id = '{AccountId}'
```

```sql
-- CAQH Identifier
SELECT Id, IdValue, PRM_AttestationDate__c, PRM_Pending__c, PRM_Type__c
FROM Identifier
WHERE ParentRecordId = '{AccountId}' AND PRM_Type__c = 'CAQH'
```

```sql
-- Address
SELECT Id, PRM_AddressLine1__c, PRM_AddressLine2__c, 
       PRM_City__c, PRM_State__c, PRM_Zip__c, PRM_County__c
FROM Address
WHERE ParentId = '{AccountId}'
```

```sql
-- NPI
SELECT Id, Npi, Name
FROM HealthcareProviderNpi
WHERE AccountId = '{AccountId}'
```

```sql
-- Business Licenses
SELECT Id, LicenseNumber, prm_licensestate__c, LicenseClass, ContactId
FROM BusinessLicense
WHERE Contact.AccountId = '{AccountId}' AND LicenseClass = 'SBRD'
ORDER BY LastModifiedDate DESC
```

```sql
-- Person Education
SELECT Id, Name, PRM_EndDate__c, PRM_Institution__r.Name, ContactId
FROM PersonEducation
WHERE Contact.AccountId = '{AccountId}'
```

```sql
-- Healthcare Provider Taxonomy
SELECT Id, IsPrimaryTaxonomy, Taxonomy.Name, 
       Taxonomy.PRM_NPDBLicensureCodeMD__c, 
       Taxonomy.PRM_NPDBLicensureCodeDO__c,
       PRM_ProviderType__r.Name, PRM_ProviderType__r.PRM_ProviderTypeCode__c
FROM HealthcareProviderTaxonomy
WHERE AccountId = '{AccountId}'
```

```sql
-- Existing Individual Applications
SELECT Id, ApplicationType, PRM_Stage__c, Status, Category, 
       PRM_CAQHAccessible__c, RecordType.Name, CreatedDate
FROM IndividualApplication
WHERE AccountId = '{AccountId}'
ORDER BY CreatedDate DESC
```

---

## Dashboard Implementation Notes

### For Dashboard UI:
1. **Section Layout**: Organize into tabs:
   - Batch Status
   - Accounts Due
   - Case Managers
   - Data Validation
   - Errors & Logs
   - Manual Investigation

2. **Dynamic Filters**:
   - Date selector (default: TODAY)
   - Account ID search
   - Status filter (Success/Failed/Pending)

3. **Color Coding**:
   - 🟢 Green: Successful processing
   - 🟡 Yellow: Missing non-critical data
   - 🔴 Red: Critical errors/missing data

4. **Refresh Options**:
   - Auto-refresh every 5 minutes during batch execution
   - Manual refresh button
   - Last updated timestamp

5. **Export Capability**:
   - Export query results to CSV
   - Generate full report for specific date

### Query Execution Order for Investigation:
1. Start with Section 1 (Batch Status) - confirm batch ran
2. Check Section 5 (Exception Logs) - identify error patterns
3. Run Section 11 (Readiness Report) - see affected accounts
4. Use Section 12 (Manual Troubleshooting) - deep dive specific accounts
5. Check Section 3 (Case Manager Status) - verify created records
6. Review Section 4 (Data Validation) - identify data gaps

### Critical Alerts to Configure:
- ⚠️ Batch failed with errors
- ⚠️ More than 10% of accounts have missing required data
- ⚠️ Duplicate case managers created
- ⚠️ Case managers not linked to cases
- ⚠️ CAQH API failures

---

## Additional Monitoring Recommendations

### 1. Setup Platform Events for Real-Time Monitoring
Consider creating platform events in the batch to publish:
- Batch start/completion
- Account processing failures
- CAQH API failures
- DML operation failures

### 2. Custom Metadata for Configuration
Store in `PRM_CAQHDateRangeSetting__c`:
- Alert thresholds
- Retry configurations
- Expected processing volumes

### 3. Scheduled Report
Create a scheduled report that runs after batch completion:
- Summary of accounts processed
- Count of case managers created
- Count of failures
- Data quality metrics

---

## Quick Reference: Common Failure Scenarios

| Failure Scenario | Root Cause | Query to Run | Resolution |
|-----------------|------------|--------------|------------|
| No case managers created | Batch didn't run or all accounts skipped | 1.1, 9.1 | Check batch schedule and existing recred IAs |
| Case managers created but not linked | linkRecords() failed | 3.2, 3.3 | Check for DML errors in exception logs |
| Missing adverse action logs | Missing address data | 4.1, 5.3 | Ensure accounts have valid addresses |
| Duplicate case managers | Batch ran multiple times or duplicate detection failed | 3.4, 7.2 | Check batch schedule and CDM duplicate prevention |
| CAQH validation failures | API timeout or expired attestation | 5.2, 8.2 | Check CAQH API status and attestation dates |
| Processing stopped mid-batch | Governor limits or exception | 1.2, 5.1 | Check AsyncApexJob for limits and exception logs |

---

**Last Updated:** 2026-04-06  
**Batch Class:** PRM_CheckCAQHAccessOnDueAccountsBatch  
**Related Classes:** PRM_CheckCAQHExecuteHelper, PRM_CheckCAQHRecordInitHelper, PRM_CheckCAQHDataHelper
