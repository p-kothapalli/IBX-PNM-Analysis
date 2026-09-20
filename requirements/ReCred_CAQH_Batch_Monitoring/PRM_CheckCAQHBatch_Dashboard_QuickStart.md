# ReCred CAQH Batch - Admin Quick Start Guide

## 🚨 When the Batch Fails - What to Check First

### Step 1: Did the batch actually run?
```sql
SELECT Id, Status, NumberOfErrors, JobItemsProcessed, TotalJobItems, 
       CompletedDate, ExtendedStatus
FROM AsyncApexJob
WHERE ApexClass.Name = 'PRM_CheckCAQHAccessOnDueAccountsBatch'
  AND CreatedDate = TODAY
ORDER BY CreatedDate DESC
LIMIT 1
```
**Look for:** 
- Status = 'Failed' or 'Aborted'
- NumberOfErrors > 0

---

### Step 2: What errors occurred?
```sql
SELECT Id, PRM_ClassName__c, PRM_TypeName__c, PRM_Message__c, 
       PRM_StackTrace__c, CreatedDate
FROM PRM_ExceptionLog__c
WHERE PRM_ClassName__c = 'PRM_CheckCAQHAccessOnDueAccountsBatch'
  AND CreatedDate = TODAY
ORDER BY CreatedDate DESC
```
**Common Errors:**
- "Address is null" → Missing address data
- "REQUIRED_FIELD_MISSING" → Missing required fields on records
- "UNABLE_TO_LOCK_ROW" → Record locking issues
- "Callout timeout" → CAQH API issues

---

### Step 3: Were any case managers created?
```sql
SELECT COUNT(Id) 
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_ReCredentialing'
  AND CreatedDate = TODAY
```
**If count = 0:** No records created - check if accounts were in scope (Step 4)  
**If count > 0:** Some succeeded - identify which failed (Step 5)

---

### Step 4: How many accounts should have been processed?
```sql
-- First, get the date range configuration:
SELECT PRM_DueDays__c, PRM_StartDate__c, PRM_EndDate__c
FROM PRM_CAQHDateRangeSetting__c
WHERE Name = 'ReCredCAQHDateRange'
LIMIT 1
```

Then check accounts in scope:
```sql
SELECT COUNT(Id)
FROM Account
WHERE RecordType.DeveloperName = 'PRM_Practitioner'
  AND IsActive = true
  AND PRM_DelegatedOnly__c = false
  AND PRM_PNC__c = false
  AND PRM_ReCredDueDate__c = NEXT_N_DAYS:180  -- Adjust based on config
```

---

### Step 5: Which accounts failed?
```sql
-- Accounts due but no case manager created
SELECT Id, Name, PRM_ReCredDueDate__c, PersonContactId
FROM Account
WHERE RecordType.DeveloperName = 'PRM_Practitioner'
  AND IsActive = true
  AND PRM_DelegatedOnly__c = false
  AND PRM_PNC__c = false
  AND PRM_ReCredDueDate__c = NEXT_N_DAYS:180
  AND Id NOT IN (
    SELECT AccountId 
    FROM IndividualApplication 
    WHERE RecordType.DeveloperName = 'PRM_ReCredentialing'
      AND CreatedDate = TODAY
  )
```

---

## 🔍 Deep Dive: Why Did Specific Accounts Fail?

### Check 1: Missing CAQH Identifier
```sql
SELECT 'Missing CAQH Identifier' AS Issue, COUNT(Id) AS Count
FROM Account
WHERE RecordType.DeveloperName = 'PRM_Practitioner'
  AND IsActive = true
  AND PRM_ReCredDueDate__c = NEXT_N_DAYS:180
  AND Id NOT IN (
    SELECT ParentRecordId 
    FROM Identifier 
    WHERE PRM_Type__c = 'CAQH'
  )
```

### Check 2: Missing Address
```sql
SELECT 'Missing Address' AS Issue, COUNT(Id) AS Count
FROM Account
WHERE RecordType.DeveloperName = 'PRM_Practitioner'
  AND IsActive = true
  AND PRM_ReCredDueDate__c = NEXT_N_DAYS:180
  AND Id NOT IN (
    SELECT ParentId 
    FROM Address 
    WHERE ParentId != null
  )
```

### Check 3: Missing NPI
```sql
SELECT 'Missing NPI' AS Issue, COUNT(Id) AS Count
FROM Account
WHERE RecordType.DeveloperName = 'PRM_Practitioner'
  AND IsActive = true
  AND PRM_ReCredDueDate__c = NEXT_N_DAYS:180
  AND Id NOT IN (
    SELECT AccountId 
    FROM HealthcareProviderNpi 
    WHERE AccountId != null
  )
```

### Check 4: Missing Business License
```sql
SELECT 'Missing License' AS Issue, COUNT(Id) AS Count
FROM Account
WHERE RecordType.DeveloperName = 'PRM_Practitioner'
  AND IsActive = true
  AND PRM_ReCredDueDate__c = NEXT_N_DAYS:180
  AND PersonContactId NOT IN (
    SELECT ContactId 
    FROM BusinessLicense 
    WHERE LicenseClass = 'SBRD'
  )
```

---

## 🛠️ Fix Common Issues

### Issue: "Address is null" errors

**Diagnosis:**
```sql
SELECT acc.Id, acc.Name, 
       (SELECT COUNT() FROM Addresses) AS AddressCount
FROM Account acc
WHERE acc.Id IN (
  SELECT PRM_RecordId__c 
  FROM PRM_ExceptionLog__c 
  WHERE PRM_Message__c = 'Address is null'
    AND CreatedDate = TODAY
)
```

**Resolution:**
1. Add missing address records to the accounts
2. Ensure address has required fields: PRM_City__c, PRM_State__c, PRM_Zip__c
3. Re-run batch for these accounts only

---

### Issue: Case managers created but not linked to cases

**Diagnosis:**
```sql
SELECT Id, AccountId, Account.Name, Status, ApplicationCaseId
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_ReCredentialing'
  AND CreatedDate = TODAY
  AND ApplicationCaseId = null
```

**Resolution:**
1. Check if corresponding cases exist
2. If cases exist, manually link them
3. If cases don't exist, check exception logs for case creation failures

---

### Issue: Duplicate case managers created

**Diagnosis:**
```sql
SELECT AccountId, Account.Name, COUNT(Id) AS DuplicateCount
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_ReCredentialing'
  AND CreatedDate = TODAY
  AND Status IN ('Pending NPDB', 'Pending CAQH Access')
GROUP BY AccountId, Account.Name
HAVING COUNT(Id) > 1
```

**Resolution:**
1. Identify the correct case manager to keep
2. Delete duplicate records
3. Check if batch ran multiple times unintentionally

---

## 📊 Daily Health Check Dashboard

Run this query every morning to get a summary:

```sql
-- Summary Report
SELECT 
  'Batch Ran Today' AS Metric,
  CASE WHEN COUNT(Id) > 0 THEN 'Yes' ELSE 'No' END AS Status
FROM AsyncApexJob
WHERE ApexClass.Name = 'PRM_CheckCAQHAccessOnDueAccountsBatch'
  AND CreatedDate = TODAY

UNION ALL

SELECT 
  'Case Managers Created',
  CAST(COUNT(Id) AS TEXT)
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_ReCredentialing'
  AND CreatedDate = TODAY

UNION ALL

SELECT 
  'Errors Logged',
  CAST(COUNT(Id) AS TEXT)
FROM PRM_ExceptionLog__c
WHERE PRM_ClassName__c = 'PRM_CheckCAQHAccessOnDueAccountsBatch'
  AND CreatedDate = TODAY

UNION ALL

SELECT 
  'Case Managers Not Linked',
  CAST(COUNT(Id) AS TEXT)
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_ReCredentialing'
  AND CreatedDate = TODAY
  AND ApplicationCaseId = null

UNION ALL

SELECT 
  'Duplicate Case Managers',
  CAST(COUNT(DISTINCT AccountId) AS TEXT)
FROM (
  SELECT AccountId, COUNT(Id) AS DupCount
  FROM IndividualApplication
  WHERE RecordType.DeveloperName = 'PRM_ReCredentialing'
    AND CreatedDate = TODAY
  GROUP BY AccountId
  HAVING COUNT(Id) > 1
)
```

---

## 🔄 Manual Batch Re-run for Failed Accounts

If you need to manually re-process failed accounts:

### Option 1: Anonymous Apex (for small sets)
```apex
// Get failed account IDs
Set<Id> failedAccountIds = new Set<Id>{'001XXXXXXXXXX', '001YYYYYYYYYY'};

// Query accounts with all related data
List<Account> accounts = [
  SELECT Id, PersonContactId, PRM_ReCredDueDate__c, PersonBirthdate, Name,
         (SELECT Id, IdValue, ParentRecordId, PRM_AttestationDate__c 
          FROM Identifiers WHERE PRM_Type__c = 'CAQH')
  FROM Account
  WHERE Id IN :failedAccountIds
];

// Initialize helpers
PRM_CheckCAQHExecuteHelper.RelatedDataWrapper dataWrapper = 
  PRM_CheckCAQHExecuteHelper.fetchRelatedData(accounts);
PRM_CheckCAQHExecuteHelper.RecordsToInsertWrapper recordsWrapper = 
  new PRM_CheckCAQHExecuteHelper.RecordsToInsertWrapper();

// Process accounts
Integer count = 0;
for (Account acc : accounts) {
  PRM_CheckCAQHExecuteHelper.processAccount(acc, dataWrapper, recordsWrapper, count);
  count++;
}

// Insert records
if (!recordsWrapper.caseManagersToInsertMap.isEmpty()) {
  Database.insert(recordsWrapper.caseManagersToInsertMap.values(), AccessLevel.USER_MODE);
}
if (!recordsWrapper.casesToInsertMap.isEmpty()) {
  Database.insert(recordsWrapper.casesToInsertMap.values(), AccessLevel.USER_MODE);
}
if (!recordsWrapper.caseManagersToInsertMap.keySet().isEmpty()) {
  PRM_CheckCAQHExecuteHelper.linkRecords(recordsWrapper);
}

System.debug('Processed: ' + count + ' accounts');
```

### Option 2: Re-run Batch (for large sets)
```apex
// Execute batch for all failed accounts
Database.executeBatch(new PRM_CheckCAQHAccessOnDueAccountsBatch(), 50);
```

---

## 📋 Pre-Batch Validation Checklist

Run these checks **before** the scheduled batch runs:

### ✅ Configuration Check
```sql
SELECT Name, PRM_DueDays__c, PRM_StartDate__c, PRM_EndDate__c, PRM_BatchSize__c
FROM PRM_CAQHDateRangeSetting__c
WHERE Name = 'ReCredCAQHDateRange'
```

### ✅ Data Quality Check
```sql
-- Accounts with missing critical data
SELECT 
  acc.Id, 
  acc.Name,
  CASE WHEN (SELECT COUNT() FROM Identifiers WHERE PRM_Type__c = 'CAQH') = 0 
       THEN 'Missing CAQH' ELSE 'OK' END AS CAQH_Status,
  CASE WHEN (SELECT COUNT() FROM Addresses) = 0 
       THEN 'Missing Address' ELSE 'OK' END AS Address_Status,
  CASE WHEN (SELECT COUNT() FROM HealthcareProviderNpis) = 0 
       THEN 'Missing NPI' ELSE 'OK' END AS NPI_Status
FROM Account acc
WHERE acc.RecordType.DeveloperName = 'PRM_Practitioner'
  AND acc.IsActive = true
  AND acc.PRM_DelegatedOnly__c = false
  AND acc.PRM_PNC__c = false
  AND acc.PRM_ReCredDueDate__c = NEXT_N_DAYS:180
LIMIT 100
```

### ✅ Duplicate Prevention Check
```sql
-- Check for existing active recred case managers
SELECT AccountId, Account.Name, COUNT(Id) AS ExistingRecredCount
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_ReCredentialing'
  AND Status NOT IN ('Approved', 'Denied', 'Terminate')
  AND Account.PRM_ReCredDueDate__c = NEXT_N_DAYS:180
GROUP BY AccountId, Account.Name
HAVING COUNT(Id) > 0
```

---

## 📞 Escalation Path

**Level 1:** Run quick checks (Steps 1-3)  
**Level 2:** Run deep dive queries (Step 5 + individual checks)  
**Level 3:** Review exception logs and stack traces  
**Level 4:** Contact development team with:
- AsyncApexJob ID
- Exception log records
- Sample failed account IDs
- Complete dashboard summary

---

## 🎯 Key Performance Indicators

**Healthy Batch Run:**
- ✅ Status: Completed
- ✅ NumberOfErrors: 0
- ✅ Case Managers Created: Matches accounts in scope
- ✅ Case Managers Linked: 100%
- ✅ No duplicate case managers
- ✅ No exception logs

**Requires Investigation:**
- ⚠️ Status: Completed but NumberOfErrors > 0
- ⚠️ Case Managers Created < 90% of expected
- ⚠️ Exception logs > 5

**Critical Issues:**
- 🚨 Status: Failed or Aborted
- 🚨 Case Managers Created: 0
- 🚨 Exception logs > 20
- 🚨 Duplicate case managers detected

---

**Version:** 1.0  
**Last Updated:** 2026-04-06  
**For Questions:** Contact Salesforce Admin Team
