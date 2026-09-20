# ReCred CAQH Batch - Quick Troubleshooting Card
**Print this page and keep it handy for quick reference**

---

## 🔍 5-MINUTE HEALTH CHECK

### 1️⃣ Did the batch run today?
```sql
SELECT Status, NumberOfErrors, JobItemsProcessed, TotalJobItems
FROM AsyncApexJob
WHERE ApexClass.Name = 'PRM_CheckCAQHAccessOnDueAccountsBatch'
  AND CreatedDate = TODAY
LIMIT 1
```
✅ **Expected:** Status = 'Completed', NumberOfErrors = 0

---

### 2️⃣ How many case managers were created?
```sql
SELECT COUNT(Id) 
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_ReCredentialing'
  AND CreatedDate = TODAY
```
✅ **Expected:** Should match the number of accounts due for recredentialing

---

### 3️⃣ Any errors logged?
```sql
SELECT COUNT(Id) 
FROM PRM_ExceptionLog__c
WHERE PRM_ClassName__c = 'PRM_CheckCAQHAccessOnDueAccountsBatch'
  AND CreatedDate = TODAY
```
✅ **Expected:** 0 errors

---

## ⚠️ COMMON ERROR CODES

| Error Message | Meaning | Quick Fix |
|--------------|---------|-----------|
| **"Address is null"** | Account missing address | Add address with City, State, Zip |
| **"REQUIRED_FIELD_MISSING"** | Missing required fields | Check PRM_AdverseActionLog__c fields |
| **"UNABLE_TO_LOCK_ROW"** | Record locked by another process | Retry batch or wait for lock release |
| **"Callout timeout"** | CAQH API not responding | Check CAQH service status, retry later |
| **"Duplicate value"** | Duplicate record detected | Check for existing case managers |

---

## 🚨 CRITICAL CHECKS

### Missing CAQH Identifiers
```sql
SELECT Id, Name FROM Account
WHERE RecordType.DeveloperName = 'PRM_Practitioner'
  AND PRM_ReCredDueDate__c = NEXT_N_DAYS:180
  AND Id NOT IN (SELECT ParentRecordId FROM Identifier WHERE PRM_Type__c = 'CAQH')
```

### Case Managers Not Linked to Cases
```sql
SELECT COUNT(Id) FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_ReCredentialing'
  AND CreatedDate = TODAY
  AND ApplicationCaseId = null
```

### Duplicate Case Managers
```sql
SELECT AccountId, COUNT(Id) FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_ReCredentialing'
  AND CreatedDate = TODAY
GROUP BY AccountId
HAVING COUNT(Id) > 1
```

---

## 📊 HEALTH STATUS INDICATORS

| Indicator | Healthy | Warning | Critical |
|-----------|---------|---------|----------|
| **Batch Status** | Completed | Completed with errors | Failed/Aborted |
| **Success Rate** | 100% | 90-99% | <90% |
| **Exception Count** | 0 | 1-5 | >5 |
| **Unlinking Case Managers** | 0 | 1-2 | >2 |

---

## 🛠️ INVESTIGATION DEEP DIVE

### Check Specific Account (Replace {AccountId})
```sql
-- Account Details
SELECT Id, Name, PRM_ReCredDueDate__c, PersonContactId
FROM Account WHERE Id = '{AccountId}'

-- CAQH Identifier
SELECT IdValue, PRM_AttestationDate__c FROM Identifier
WHERE ParentRecordId = '{AccountId}' AND PRM_Type__c = 'CAQH'

-- Address
SELECT PRM_City__c, PRM_State__c, PRM_Zip__c FROM Address
WHERE ParentId = '{AccountId}'

-- NPI
SELECT Npi FROM HealthcareProviderNpi WHERE AccountId = '{AccountId}'

-- Business License
SELECT LicenseNumber, prm_licensestate__c FROM BusinessLicense
WHERE Contact.AccountId = '{AccountId}' AND LicenseClass = 'SBRD'
```

---

## 📞 ESCALATION CHECKLIST

Before escalating to development team, gather:

✅ AsyncApexJob ID from Query #1  
✅ Exception log records (IDs or screenshots)  
✅ At least 3 sample failed account IDs  
✅ Batch configuration (PRM_CAQHDateRangeSetting__c)  
✅ Expected vs actual case manager count  

---

## 💡 QUICK TIPS

1. **Auto-Refresh:** Batch runs overnight. Check dashboard around 8 AM.
2. **Date Range:** Check `PRM_CAQHDateRangeSetting__c` for current configuration.
3. **Manual Rerun:** Never rerun batch without checking for duplicates first.
4. **Missing Data:** Most failures = missing required data (CAQH, Address, NPI).
5. **CAQH API:** If many callout timeouts, wait 30 mins and rerun.

---

## 📅 DAILY ROUTINE

**Morning (8:00 AM):**
- ✅ Run Query #1 (Batch Status)
- ✅ Run Query #2 (Case Managers Created)
- ✅ Run Query #3 (Error Count)

**If Issues Found:**
- ✅ Run all Critical Checks
- ✅ Gather Investigation Data
- ✅ Fix Missing Data or Escalate

**End of Day:**
- ✅ Verify all case managers linked
- ✅ Document any fixes applied
- ✅ Update team on status

---

## 🔗 USEFUL LINKS

- **Batch Class:** PRM_CheckCAQHAccessOnDueAccountsBatch
- **Helper Classes:** PRM_CheckCAQHExecuteHelper, PRM_CheckCAQHRecordInitHelper
- **Related Objects:** IndividualApplication, Case, PRM_AdverseActionLog__c
- **Exception Logs:** PRM_ExceptionLog__c

---

## 📋 MANUAL RERUN (Last Resort)

```apex
// Anonymous Apex - Use with caution!
Database.executeBatch(new PRM_CheckCAQHAccessOnDueAccountsBatch(), 50);
```
⚠️ **Warning:** Only run after confirming no duplicates will be created!

---

**Version:** 1.0  
**Print Date:** 2026-04-06  
**Keep Updated:** Check for new version quarterly
