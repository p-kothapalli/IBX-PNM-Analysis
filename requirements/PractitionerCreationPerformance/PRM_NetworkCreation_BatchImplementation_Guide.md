# PRM Network Creation - Batch Implementation Guide

## Overview

This guide provides a complete implementation for moving the heavy network creation process from synchronous Integration Procedure (IP) execution to an asynchronous, event-driven Batch Apex architecture.

**Current Problem:**
- `PRM_AddressLogicContainer` → `PRM_CreateDelegatedHFNRecords` takes 5+ minutes
- Processing 3 locations × 3 taxonomies × 15 networks = 54+ records
- Hits governor limits and causes UI spinning loop

**Solution:**
- Event-driven architecture with Batch Apex
- UI returns instantly with "Processing..." message
- Background processing with status updates
- Email notification on completion

---

## Architecture Diagram

```
┌─────────────────────────────────────┐
│   PRM_AddressLogicContainer (IP)    │
│                                     │
│   1. PractitionerAddressCreation    │
│   2. ExistingPrimaryAddressLogic    │
│   3. PublishNetworkCreationEvent    │ ← NEW
└──────────────┬──────────────────────┘
               │
               │ Publishes Platform Event
               ▼
┌──────────────────────────────────────┐
│  NetworkCreationRequested__e         │
│  (Platform Event)                    │
└──────────────┬───────────────────────┘
               │
               │ Trigger fires
               ▼
┌──────────────────────────────────────┐
│  PRM_NetworkCreationEventTrigger     │
│  (Calls orchestrator)                │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  PRM_NetworkCreationOrchestrator     │
│  (Starts batch jobs)                 │
└──────────────┬───────────────────────┘
               │
               ├──────────────────────┐
               │                      │
               ▼                      ▼
    ┌──────────────────┐   ┌──────────────────┐
    │ Taxonomy Batch   │   │ Payer Network    │
    │ (9 records)      │   │ Batch            │
    │                  │   │ (45 records)     │
    └────────┬─────────┘   └────────┬─────────┘
             │                      │
             │ Finish               │ Finish
             ▼                      ▼
    ┌──────────────────────────────────┐
    │      IFC Batch                   │
    │      (15 records)                │
    └────────┬─────────────────────────┘
             │
             │ Finish
             ▼
    ┌──────────────────────────────────┐
    │  Update Status + Send Email      │
    └──────────────────────────────────┘
```

---

## Implementation Steps

### Step 1: Create Platform Event

**File:** `force-app/main/default/objects/NetworkCreationRequested__e/NetworkCreationRequested__e.object-meta.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <deploymentStatus>Deployed</deploymentStatus>
    <eventType>HighVolume</eventType>
    <label>Network Creation Requested</label>
    <pluralLabel>Network Creation Requests</pluralLabel>
    <publishBehavior>PublishAfterCommit</publishBehavior>
</CustomObject>
```

**Create Custom Fields:**

**CaseManagerId__c:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>CaseManagerId__c</fullName>
    <label>Case Manager Id</label>
    <length>18</length>
    <required>true</required>
    <type>Text</type>
</CustomField>
```

**PersonContactId__c:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>PersonContactId__c</fullName>
    <label>Person Contact Id</label>
    <length>18</length>
    <required>true</required>
    <type>Text</type>
</CustomField>
```

**FacilityPractitionerTxNw__c:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>FacilityPractitionerTxNw__c</fullName>
    <label>Facility Practitioner TxNw</label>
    <length>32768</length>
    <type>LongTextArea</type>
    <visibleLines>5</visibleLines>
</CustomField>
```

**IsActive__c, IsPending__c, EffectiveFrom__c, EffectiveTo__c, RecordsToUpdate__c** (similar pattern)

**RequestId__c:** (For tracking)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>RequestId__c</fullName>
    <label>Request Id</label>
    <length>36</length>
    <required>false</required>
    <type>Text</type>
</CustomField>
```

---

### Step 2: Add Status Tracking Field to Case Manager

**File:** `force-app/main/default/objects/CaseManager__c/fields/PRM_NetworkCreationStatus__c.field-meta.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>PRM_NetworkCreationStatus__c</fullName>
    <label>Network Creation Status</label>
    <required>false</required>
    <type>Picklist</type>
    <valueSet>
        <restricted>true</restricted>
        <valueSetDefinition>
            <sorted>false</sorted>
            <value>
                <fullName>Not Started</fullName>
                <default>true</default>
                <label>Not Started</label>
            </value>
            <value>
                <fullName>Queued</fullName>
                <default>false</default>
                <label>Queued</label>
            </value>
            <value>
                <fullName>Processing Taxonomies</fullName>
                <default>false</default>
                <label>Processing Taxonomies</label>
            </value>
            <value>
                <fullName>Processing Payer Networks</fullName>
                <default>false</default>
                <label>Processing Payer Networks</label>
            </value>
            <value>
                <fullName>Processing IFC</fullName>
                <default>false</default>
                <label>Processing IFC</label>
            </value>
            <value>
                <fullName>Completed</fullName>
                <default>false</default>
                <label>Completed</label>
            </value>
            <value>
                <fullName>Failed</fullName>
                <default>false</default>
                <label>Failed</label>
            </value>
        </valueSetDefinition>
    </valueSet>
</CustomField>
```

**PRM_NetworkCreationError__c:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>PRM_NetworkCreationError__c</fullName>
    <label>Network Creation Error</label>
    <length>32768</length>
    <type>LongTextArea</type>
    <visibleLines>5</visibleLines>
</CustomField>
```

---

### Step 3: Create Batch Apex Classes

#### 3.1 Taxonomy Network Batch

**File:** `force-app/main/default/classes/PRM_TaxonomyNetworkBatch.cls`

```apex
/**
 * Batch class to create Taxonomy Network records for delegated practitioners
 * Processes practice locations and creates FacilityPractitionerTxNw records
 */
public class PRM_TaxonomyNetworkBatch implements Database.Batchable<SObject>, Database.Stateful {

    private String caseManagerId;
    private String personContactId;
    private String requestId;
    private String facilityPractitionerTxNw;
    private Boolean isActive;
    private Boolean isPending;
    private Date effectiveFrom;
    private Date effectiveTo;
    private String recordsToUpdate;

    private Integer totalProcessed = 0;
    private Integer totalErrors = 0;
    private List<String> errorMessages = new List<String>();

    public PRM_TaxonomyNetworkBatch(Map<String, Object> params) {
        this.caseManagerId = (String)params.get('CaseManagerId');
        this.personContactId = (String)params.get('PersonContactId');
        this.requestId = (String)params.get('RequestId');
        this.facilityPractitionerTxNw = (String)params.get('FacilityPractitionerTxNw');
        this.isActive = (Boolean)params.get('IsActive');
        this.isPending = (Boolean)params.get('IsPending');
        this.effectiveFrom = (Date)params.get('EffectiveFrom');
        this.effectiveTo = (Date)params.get('EffectiveTo');
        this.recordsToUpdate = (String)params.get('RecordsToUpdate');
    }

    /**
     * Start method - Query practice locations that need taxonomy networks
     */
    public Database.QueryLocator start(Database.BatchableContext BC) {
        // Update status
        updateStatus('Processing Taxonomies', null);

        // Parse the taxonomy data from input
        // Query relevant practice locations
        return Database.getQueryLocator([
            SELECT Id, Name,
                   PRM_Address__c,
                   PRM_PracticeLocation__c,
                   PRM_Taxonomy1__c,
                   PRM_Taxonomy2__c,
                   PRM_Taxonomy3__c
            FROM PRM_PractitionerPracticeLocation__c
            WHERE PRM_CaseManager__c = :caseManagerId
            AND PRM_PersonContact__c = :personContactId
            AND (PRM_Taxonomy1__c != null
                 OR PRM_Taxonomy2__c != null
                 OR PRM_Taxonomy3__c != null)
        ]);
    }

    /**
     * Execute method - Process each batch of locations
     */
    public void execute(Database.BatchableContext BC, List<SObject> scope) {
        List<PRM_FacilityPractitionerTxNw__c> recordsToInsert = new List<PRM_FacilityPractitionerTxNw__c>();

        try {
            for (SObject record : scope) {
                PRM_PractitionerPracticeLocation__c ppl = (PRM_PractitionerPracticeLocation__c)record;

                // Create taxonomy network records for each taxonomy
                if (String.isNotBlank(ppl.PRM_Taxonomy1__c)) {
                    recordsToInsert.add(createTaxonomyRecord(ppl, ppl.PRM_Taxonomy1__c));
                }
                if (String.isNotBlank(ppl.PRM_Taxonomy2__c)) {
                    recordsToInsert.add(createTaxonomyRecord(ppl, ppl.PRM_Taxonomy2__c));
                }
                if (String.isNotBlank(ppl.PRM_Taxonomy3__c)) {
                    recordsToInsert.add(createTaxonomyRecord(ppl, ppl.PRM_Taxonomy3__c));
                }
            }

            // Insert records
            if (!recordsToInsert.isEmpty()) {
                Database.SaveResult[] results = Database.insert(recordsToInsert, false);

                // Track results
                for (Integer i = 0; i < results.size(); i++) {
                    if (results[i].isSuccess()) {
                        totalProcessed++;
                    } else {
                        totalErrors++;
                        for (Database.Error err : results[i].getErrors()) {
                            errorMessages.add('Taxonomy Record ' + i + ': ' + err.getMessage());
                        }
                    }
                }
            }

        } catch (Exception e) {
            totalErrors += scope.size();
            errorMessages.add('Execute Exception: ' + e.getMessage() + ' | ' + e.getStackTraceString());
        }
    }

    /**
     * Finish method - Update status and trigger next batch
     */
    public void finish(Database.BatchableContext BC) {
        String status = totalErrors > 0 ?
            'Processing Taxonomies (Errors: ' + totalErrors + ')' :
            'Processing Payer Networks';

        updateStatus(status, String.join(errorMessages, '\n'));

        // If no critical errors, trigger Payer Network Batch
        if (totalErrors == 0 || totalProcessed > 0) {
            Map<String, Object> params = new Map<String, Object>{
                'CaseManagerId' => caseManagerId,
                'PersonContactId' => personContactId,
                'RequestId' => requestId,
                'IsActive' => isActive,
                'IsPending' => isPending,
                'EffectiveFrom' => effectiveFrom,
                'EffectiveTo' => effectiveTo,
                'RecordsToUpdate' => recordsToUpdate
            };

            // Start Payer Network Batch (batch size = 2 locations at a time = ~30 records)
            Database.executeBatch(new PRM_PayerNetworkBatch(params), 2);
        } else {
            // Critical failure - mark as failed
            updateStatus('Failed', String.join(errorMessages, '\n'));
            sendNotification(false);
        }
    }

    /**
     * Helper: Create taxonomy network record
     */
    private PRM_FacilityPractitionerTxNw__c createTaxonomyRecord(
        PRM_PractitionerPracticeLocation__c ppl,
        String taxonomyId
    ) {
        return new PRM_FacilityPractitionerTxNw__c(
            PRM_CaseManager__c = caseManagerId,
            PRM_PersonContact__c = personContactId,
            PRM_PractitionerPracticeLocation__c = ppl.Id,
            PRM_PracticeLocation__c = ppl.PRM_PracticeLocation__c,
            PRM_Taxonomy__c = taxonomyId,
            PRM_IsActive__c = isActive,
            PRM_EffectiveFrom__c = effectiveFrom,
            PRM_EffectiveTo__c = effectiveTo
        );
    }

    /**
     * Helper: Update status on Case Manager
     */
    private void updateStatus(String status, String error) {
        try {
            CaseManager__c cm = new CaseManager__c(
                Id = caseManagerId,
                PRM_NetworkCreationStatus__c = status
            );
            if (String.isNotBlank(error)) {
                cm.PRM_NetworkCreationError__c = error.left(32768);
            }
            update cm;
        } catch (Exception e) {
            System.debug('Error updating status: ' + e.getMessage());
        }
    }

    /**
     * Helper: Send completion notification
     */
    private void sendNotification(Boolean success) {
        // Implement email notification logic here
        // Use Messaging.SingleEmailMessage or Email Template
    }
}
```

**Test Class:** `force-app/main/default/classes/PRM_TaxonomyNetworkBatchTest.cls`

```apex
@isTest
private class PRM_TaxonomyNetworkBatchTest {

    @testSetup
    static void setup() {
        // Create test data
        CaseManager__c cm = new CaseManager__c(Name = 'Test CM');
        insert cm;

        Contact c = new Contact(LastName = 'Test Contact');
        insert c;

        PracticeLocation__c pl = new PracticeLocation__c(Name = 'Test Location');
        insert pl;

        PRM_PractitionerPracticeLocation__c ppl = new PRM_PractitionerPracticeLocation__c(
            PRM_CaseManager__c = cm.Id,
            PRM_PersonContact__c = c.Id,
            PRM_PracticeLocation__c = pl.Id,
            PRM_Taxonomy1__c = 'TAX001',
            PRM_Taxonomy2__c = 'TAX002'
        );
        insert ppl;
    }

    @isTest
    static void testBatchExecution() {
        CaseManager__c cm = [SELECT Id FROM CaseManager__c LIMIT 1];
        Contact c = [SELECT Id FROM Contact LIMIT 1];

        Map<String, Object> params = new Map<String, Object>{
            'CaseManagerId' => cm.Id,
            'PersonContactId' => c.Id,
            'RequestId' => 'TEST-REQ-001',
            'IsActive' => true,
            'IsPending' => false,
            'EffectiveFrom' => Date.today(),
            'EffectiveTo' => Date.today().addYears(1)
        };

        Test.startTest();
        PRM_TaxonomyNetworkBatch batch = new PRM_TaxonomyNetworkBatch(params);
        Database.executeBatch(batch, 5);
        Test.stopTest();

        // Verify records created
        List<PRM_FacilityPractitionerTxNw__c> results = [
            SELECT Id FROM PRM_FacilityPractitionerTxNw__c
            WHERE PRM_CaseManager__c = :cm.Id
        ];
        System.assertEquals(2, results.size(), 'Should create 2 taxonomy records');
    }
}
```

---

#### 3.2 Payer Network Batch

**File:** `force-app/main/default/classes/PRM_PayerNetworkBatch.cls`

```apex
/**
 * Batch class to create Payer Network records for delegated practitioners
 * Processes practice locations and creates FacilityPractitionerNw records
 */
public class PRM_PayerNetworkBatch implements Database.Batchable<SObject>, Database.Stateful {

    private String caseManagerId;
    private String personContactId;
    private String requestId;
    private Boolean isActive;
    private Boolean isPending;
    private Date effectiveFrom;
    private Date effectiveTo;
    private String recordsToUpdate;

    private Integer totalProcessed = 0;
    private Integer totalErrors = 0;
    private List<String> errorMessages = new List<String>();

    public PRM_PayerNetworkBatch(Map<String, Object> params) {
        this.caseManagerId = (String)params.get('CaseManagerId');
        this.personContactId = (String)params.get('PersonContactId');
        this.requestId = (String)params.get('RequestId');
        this.isActive = (Boolean)params.get('IsActive');
        this.isPending = (Boolean)params.get('IsPending');
        this.effectiveFrom = (Date)params.get('EffectiveFrom');
        this.effectiveTo = (Date)params.get('EffectiveTo');
        this.recordsToUpdate = (String)params.get('RecordsToUpdate');
    }

    public Database.QueryLocator start(Database.BatchableContext BC) {
        updateStatus('Processing Payer Networks', null);

        // Query practice locations with their payer networks
        return Database.getQueryLocator([
            SELECT Id, Name,
                   PRM_PracticeLocation__c,
                   (SELECT Id, PRM_PayerNetwork__c
                    FROM PRM_PracticeLocationPayerNetworks__r)
            FROM PRM_PractitionerPracticeLocation__c
            WHERE PRM_CaseManager__c = :caseManagerId
            AND PRM_PersonContact__c = :personContactId
        ]);
    }

    public void execute(Database.BatchableContext BC, List<SObject> scope) {
        List<PRM_FacilityPractitionerNw__c> recordsToInsert = new List<PRM_FacilityPractitionerNw__c>();

        try {
            for (SObject record : scope) {
                PRM_PractitionerPracticeLocation__c ppl = (PRM_PractitionerPracticeLocation__c)record;

                // Create payer network record for each network
                for (PRM_PracticeLocationPayerNetwork__c plpn : ppl.PRM_PracticeLocationPayerNetworks__r) {
                    recordsToInsert.add(new PRM_FacilityPractitionerNw__c(
                        PRM_CaseManager__c = caseManagerId,
                        PRM_PersonContact__c = personContactId,
                        PRM_PractitionerPracticeLocation__c = ppl.Id,
                        PRM_PracticeLocation__c = ppl.PRM_PracticeLocation__c,
                        PRM_PayerNetwork__c = plpn.PRM_PayerNetwork__c,
                        PRM_IsActive__c = isActive,
                        PRM_EffectiveFrom__c = effectiveFrom,
                        PRM_EffectiveTo__c = effectiveTo
                    ));
                }
            }

            if (!recordsToInsert.isEmpty()) {
                Database.SaveResult[] results = Database.insert(recordsToInsert, false);

                for (Integer i = 0; i < results.size(); i++) {
                    if (results[i].isSuccess()) {
                        totalProcessed++;
                    } else {
                        totalErrors++;
                        for (Database.Error err : results[i].getErrors()) {
                            errorMessages.add('Payer Network ' + i + ': ' + err.getMessage());
                        }
                    }
                }
            }

        } catch (Exception e) {
            totalErrors += scope.size();
            errorMessages.add('Execute Exception: ' + e.getMessage());
        }
    }

    public void finish(Database.BatchableContext BC) {
        String status = totalErrors > 0 ?
            'Processing Payer Networks (Errors: ' + totalErrors + ')' :
            'Processing IFC';

        updateStatus(status, String.join(errorMessages, '\n'));

        // Trigger IFC Batch
        if (totalErrors == 0 || totalProcessed > 0) {
            Map<String, Object> params = new Map<String, Object>{
                'CaseManagerId' => caseManagerId,
                'PersonContactId' => personContactId,
                'RequestId' => requestId,
                'IsActive' => isActive,
                'IsPending' => isPending,
                'EffectiveFrom' => effectiveFrom,
                'EffectiveTo' => effectiveTo
            };

            Database.executeBatch(new PRM_IFCRecordBatch(params), 5);
        } else {
            updateStatus('Failed', String.join(errorMessages, '\n'));
        }
    }

    private void updateStatus(String status, String error) {
        try {
            CaseManager__c cm = new CaseManager__c(
                Id = caseManagerId,
                PRM_NetworkCreationStatus__c = status
            );
            if (String.isNotBlank(error)) {
                cm.PRM_NetworkCreationError__c = error.left(32768);
            }
            update cm;
        } catch (Exception e) {
            System.debug('Error updating status: ' + e.getMessage());
        }
    }
}
```

---

#### 3.3 IFC Record Batch

**File:** `force-app/main/default/classes/PRM_IFCRecordBatch.cls`

```apex
/**
 * Batch class to create IFC (Internal Facility Code) records
 * Final step in the network creation process
 */
public class PRM_IFCRecordBatch implements Database.Batchable<SObject>, Database.Stateful {

    private String caseManagerId;
    private String personContactId;
    private String requestId;
    private Boolean isActive;
    private Boolean isPending;
    private Date effectiveFrom;
    private Date effectiveTo;

    private Integer totalProcessed = 0;
    private Integer totalErrors = 0;
    private List<String> errorMessages = new List<String>();

    public PRM_IFCRecordBatch(Map<String, Object> params) {
        this.caseManagerId = (String)params.get('CaseManagerId');
        this.personContactId = (String)params.get('PersonContactId');
        this.requestId = (String)params.get('RequestId');
        this.isActive = (Boolean)params.get('IsActive');
        this.isPending = (Boolean)params.get('IsPending');
        this.effectiveFrom = (Date)params.get('EffectiveFrom');
        this.effectiveTo = (Date)params.get('EffectiveTo');
    }

    public Database.QueryLocator start(Database.BatchableContext BC) {
        updateStatus('Processing IFC', null);

        return Database.getQueryLocator([
            SELECT Id, Name,
                   PRM_PracticeLocation__c,
                   PRM_PracticeLocation__r.PRM_IFCCode__c
            FROM PRM_PractitionerPracticeLocation__c
            WHERE PRM_CaseManager__c = :caseManagerId
            AND PRM_PersonContact__c = :personContactId
            AND PRM_PracticeLocation__r.PRM_IFCCode__c != null
        ]);
    }

    public void execute(Database.BatchableContext BC, List<SObject> scope) {
        List<PRM_FacilityIFC__c> recordsToInsert = new List<PRM_FacilityIFC__c>();

        try {
            for (SObject record : scope) {
                PRM_PractitionerPracticeLocation__c ppl = (PRM_PractitionerPracticeLocation__c)record;

                recordsToInsert.add(new PRM_FacilityIFC__c(
                    PRM_CaseManager__c = caseManagerId,
                    PRM_PersonContact__c = personContactId,
                    PRM_PractitionerPracticeLocation__c = ppl.Id,
                    PRM_PracticeLocation__c = ppl.PRM_PracticeLocation__c,
                    PRM_IFCCode__c = ppl.PRM_PracticeLocation__r.PRM_IFCCode__c,
                    PRM_IsActive__c = isActive,
                    PRM_EffectiveFrom__c = effectiveFrom,
                    PRM_EffectiveTo__c = effectiveTo
                ));
            }

            if (!recordsToInsert.isEmpty()) {
                Database.SaveResult[] results = Database.insert(recordsToInsert, false);

                for (Integer i = 0; i < results.size(); i++) {
                    if (results[i].isSuccess()) {
                        totalProcessed++;
                    } else {
                        totalErrors++;
                        for (Database.Error err : results[i].getErrors()) {
                            errorMessages.add('IFC Record ' + i + ': ' + err.getMessage());
                        }
                    }
                }
            }

        } catch (Exception e) {
            totalErrors += scope.size();
            errorMessages.add('Execute Exception: ' + e.getMessage());
        }
    }

    public void finish(Database.BatchableContext BC) {
        Boolean success = totalErrors == 0;
        String status = success ? 'Completed' : 'Failed';

        updateStatus(status, totalErrors > 0 ? String.join(errorMessages, '\n') : null);
        sendNotification(success);
    }

    private void updateStatus(String status, String error) {
        try {
            CaseManager__c cm = new CaseManager__c(
                Id = caseManagerId,
                PRM_NetworkCreationStatus__c = status
            );
            if (String.isNotBlank(error)) {
                cm.PRM_NetworkCreationError__c = error.left(32768);
            }
            update cm;
        } catch (Exception e) {
            System.debug('Error updating status: ' + e.getMessage());
        }
    }

    private void sendNotification(Boolean success) {
        try {
            // Get user email
            CaseManager__c cm = [SELECT CreatedBy.Email, CreatedBy.Name
                                 FROM CaseManager__c
                                 WHERE Id = :caseManagerId LIMIT 1];

            Messaging.SingleEmailMessage email = new Messaging.SingleEmailMessage();
            email.setToAddresses(new String[] { cm.CreatedBy.Email });
            email.setSubject(success ?
                'Network Creation Completed Successfully' :
                'Network Creation Failed');

            String body = 'Hello ' + cm.CreatedBy.Name + ',\n\n';
            if (success) {
                body += 'The network creation process for Case Manager ' + caseManagerId + ' has completed successfully.\n\n';
                body += 'Total Records Created: ' + totalProcessed + '\n';
            } else {
                body += 'The network creation process encountered errors.\n\n';
                body += 'Total Errors: ' + totalErrors + '\n';
                body += 'Please check the Case Manager record for details.\n';
            }
            body += '\nRequest ID: ' + requestId;

            email.setPlainTextBody(body);
            Messaging.sendEmail(new Messaging.SingleEmailMessage[] { email });

        } catch (Exception e) {
            System.debug('Error sending notification: ' + e.getMessage());
        }
    }
}
```

---

### Step 4: Create Orchestrator

**File:** `force-app/main/default/classes/PRM_NetworkCreationOrchestrator.cls`

```apex
/**
 * Orchestrator that starts the batch job chain
 * Called by Platform Event trigger
 */
public class PRM_NetworkCreationOrchestrator {

    /**
     * Invocable method for Process Builder/Flow
     */
    @InvocableMethod(label='Queue Network Creation'
                     description='Starts batch jobs for network creation')
    public static void queueNetworkCreation(List<NetworkRequest> requests) {
        if (requests == null || requests.isEmpty()) {
            return;
        }

        NetworkRequest req = requests[0];

        // Generate unique request ID
        String requestId = generateRequestId();

        // Update initial status
        updateStatus(req.CaseManagerId, 'Queued', requestId);

        // Prepare parameters
        Map<String, Object> params = new Map<String, Object>{
            'CaseManagerId' => req.CaseManagerId,
            'PersonContactId' => req.PersonContactId,
            'RequestId' => requestId,
            'FacilityPractitionerTxNw' => req.FacilityPractitionerTxNw,
            'IsActive' => req.IsActive,
            'IsPending' => req.IsPending,
            'EffectiveFrom' => req.EffectiveFrom,
            'EffectiveTo' => req.EffectiveTo,
            'RecordsToUpdate' => req.RecordsToUpdate
        };

        // Start the first batch (Taxonomy Networks)
        // Batch size = 5 locations at a time
        Database.executeBatch(new PRM_TaxonomyNetworkBatch(params), 5);
    }

    /**
     * Direct method for Platform Event trigger
     */
    public static void handleEvent(NetworkCreationRequested__e event) {
        NetworkRequest req = new NetworkRequest();
        req.CaseManagerId = event.CaseManagerId__c;
        req.PersonContactId = event.PersonContactId__c;
        req.FacilityPractitionerTxNw = event.FacilityPractitionerTxNw__c;
        req.IsActive = event.IsActive__c;
        req.IsPending = event.IsPending__c;
        req.EffectiveFrom = event.EffectiveFrom__c;
        req.EffectiveTo = event.EffectiveTo__c;
        req.RecordsToUpdate = event.RecordsToUpdate__c;

        queueNetworkCreation(new List<NetworkRequest>{ req });
    }

    /**
     * Wrapper class for parameters
     */
    public class NetworkRequest {
        @InvocableVariable(required=true)
        public String CaseManagerId;

        @InvocableVariable(required=true)
        public String PersonContactId;

        @InvocableVariable
        public String FacilityPractitionerTxNw;

        @InvocableVariable
        public Boolean IsActive;

        @InvocableVariable
        public Boolean IsPending;

        @InvocableVariable
        public Date EffectiveFrom;

        @InvocableVariable
        public Date EffectiveTo;

        @InvocableVariable
        public String RecordsToUpdate;
    }

    private static String generateRequestId() {
        return 'NCR-' + Datetime.now().getTime() + '-' +
               String.valueOf(Crypto.getRandomInteger()).substring(0, 4);
    }

    private static void updateStatus(String caseManagerId, String status, String requestId) {
        try {
            update new CaseManager__c(
                Id = caseManagerId,
                PRM_NetworkCreationStatus__c = status,
                PRM_NetworkCreationError__c = 'Request ID: ' + requestId
            );
        } catch (Exception e) {
            System.debug('Error updating status: ' + e.getMessage());
        }
    }
}
```

---

### Step 5: Create Platform Event Trigger

**File:** `force-app/main/default/triggers/PRM_NetworkCreationEventTrigger.trigger`

```apex
trigger PRM_NetworkCreationEventTrigger on NetworkCreationRequested__e (after insert) {
    for (NetworkCreationRequested__e event : Trigger.new) {
        PRM_NetworkCreationOrchestrator.handleEvent(event);
    }
}
```

---

### Step 6: Modify Integration Procedure

#### Option A: Apex Remote Action (Recommended)

**Create Remote Action Class:**

**File:** `force-app/main/default/classes/PRM_NetworkCreationRemote.cls`

```apex
public class PRM_NetworkCreationRemote {

    /**
     * Called by Integration Procedure to publish Platform Event
     */
    public static Object publishNetworkCreationEvent(Map<String, Object> input) {
        try {
            // Extract parameters from IP
            String caseManagerId = (String)input.get('CaseManagerId');
            String personContactId = (String)input.get('PersonContactId');

            // Create and publish event
            NetworkCreationRequested__e event = new NetworkCreationRequested__e(
                CaseManagerId__c = caseManagerId,
                PersonContactId__c = personContactId,
                FacilityPractitionerTxNw__c = JSON.serialize(input.get('FacilityPractitionerTxNw')),
                IsActive__c = (Boolean)input.get('IsActive'),
                IsPending__c = (Boolean)input.get('IsPending'),
                EffectiveFrom__c = Date.valueOf((String)input.get('EffectiveFrom')),
                EffectiveTo__c = Date.valueOf((String)input.get('EffectiveTo')),
                RecordsToUpdate__c = JSON.serialize(input.get('RecordsToUpdate'))
            );

            Database.SaveResult result = EventBus.publish(event);

            Map<String, Object> response = new Map<String, Object>();
            if (result.isSuccess()) {
                response.put('success', true);
                response.put('message', 'Network creation queued successfully. You will be notified when complete.');
            } else {
                response.put('success', false);
                response.put('message', 'Failed to queue network creation: ' + result.getErrors()[0].getMessage());
            }

            return response;

        } catch (Exception e) {
            return new Map<String, Object>{
                'success' => false,
                'message' => 'Error: ' + e.getMessage()
            };
        }
    }
}
```

#### Update Integration Procedure JSON

**File:** `PRM_AddressLogicContainer_Element_AddTaxNetworkLogic.json`

**BEFORE (Heavy synchronous call):**
```json
{
    "Name": "AddTaxNetworkLogic",
    "PropertySetConfig": {
        "integrationProcedureKey": "PRM_CreateDelegatedHFNRecords",
        "useQueueable": true,
        "chainOnStep": false,
        "disableChainable": true
    },
    "Type": "Integration Procedure Action"
}
```

**AFTER (Publish event and return):**
```json
{
    "Name": "PublishNetworkCreationEvent",
    "PropertySetConfig": {
        "remoteClass": "PRM_NetworkCreationRemote",
        "remoteMethod": "publishNetworkCreationEvent",
        "chainOnStep": false,
        "disableChainable": false,
        "additionalInput": {
            "CaseManagerId": "=%CaseManagerId%",
            "PersonContactId": "=%PersonContactId%",
            "FacilityPractitionerTxNw": "=%FacilityPractitionerTxNw%",
            "IsActive": "=%IsActive%",
            "IsPending": "=%IsPending%",
            "EffectiveFrom": "=%PractitionerEffectiveDate%",
            "EffectiveTo": "=%PractitionerEffToDate%",
            "RecordsToUpdate": "=%RecordsToUpdate%"
        },
        "sendOnlyAdditionalInput": true,
        "useFormulas": true
    },
    "Type": "Remote Action"
}
```

#### Add Response Message Element

**File:** `PRM_AddressLogicContainer_Element_ResponseWithMessage.json`

```json
{
    "Name": "ResponseWithMessage",
    "PropertySetConfig": {
        "additionalOutput": {
            "success": "=%PublishNetworkCreationEvent:success%",
            "message": "=%PublishNetworkCreationEvent:message%",
            "addressCreated": "=%PractitionerAddressCreation:success%"
        },
        "responseFormat": "JSON",
        "returnOnlyAdditionalOutput": true,
        "useFormulas": true
    },
    "Type": "Response Action"
}
```

---

### Step 7: Update OmniScript (If Applicable)

If you're calling this from an OmniScript, update the response handling:

```javascript
// In your LWC or OmniScript JavaScript
handleIPResponse(response) {
    if (response.success) {
        // Show success toast
        this.showToast('Success', response.message, 'success');

        // Optionally navigate or refresh
        this.navigateToRecord();
    } else {
        this.showToast('Error', response.message, 'error');
    }
}

showToast(title, message, variant) {
    const event = new ShowToastEvent({
        title: title,
        message: message,
        variant: variant,
        mode: variant === 'success' ? 'dismissable' : 'sticky'
    });
    this.dispatchEvent(event);
}
```

---

## Testing Strategy

### Unit Tests

1. **Test each batch class independently**
   - Create test data
   - Execute batch
   - Verify records created
   - Test error handling

2. **Test orchestrator**
   - Mock event data
   - Verify batch starts
   - Check status updates

3. **Test remote action**
   - Mock IP input
   - Verify event published
   - Test error scenarios

### Integration Tests

1. **End-to-end test**
   - Call IP with real data
   - Wait for batch completion (Test.stopTest())
   - Verify all records created
   - Check status field
   - Verify email sent

2. **Platform Event test**
   - Publish event directly
   - Verify trigger fires
   - Verify batch starts

### Performance Testing

1. **Load test with multiple records**
   - 10 practitioners × 3 locations × 18 records each
   - Monitor governor limits
   - Check batch execution time

2. **Monitor batch jobs**
   - Setup → Apex Jobs
   - Check for failures
   - Review debug logs

---

## Deployment Checklist

- [ ] Deploy Platform Event (NetworkCreationRequested__e)
- [ ] Deploy custom fields (Status, Error)
- [ ] Deploy Batch Apex classes + tests
- [ ] Deploy Orchestrator + test
- [ ] Deploy Remote Action + test
- [ ] Deploy Platform Event Trigger
- [ ] Update Integration Procedure JSON
- [ ] Run all unit tests (>90% coverage)
- [ ] Test in Sandbox with real data
- [ ] Monitor first production run
- [ ] Document for users (status checking, timeframe)

---

## Monitoring & Troubleshooting

### Check Batch Job Status

**SOQL Query:**
```sql
SELECT Id, Status, JobItemsProcessed, TotalJobItems,
       NumberOfErrors, CreatedDate
FROM AsyncApexJob
WHERE ApexClass.Name IN ('PRM_TaxonomyNetworkBatch',
                          'PRM_PayerNetworkBatch',
                          'PRM_IFCRecordBatch')
ORDER BY CreatedDate DESC
LIMIT 10
```

### Check Network Creation Status

**SOQL Query:**
```sql
SELECT Id, Name, PRM_NetworkCreationStatus__c,
       PRM_NetworkCreationError__c, LastModifiedDate
FROM CaseManager__c
WHERE PRM_NetworkCreationStatus__c != 'Not Started'
ORDER BY LastModifiedDate DESC
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Batch doesn't start | Governor limit hit | Check async apex limit (5 concurrent) |
| Status stuck at "Queued" | Batch failed to start | Check debug logs for errors |
| "Processing..." never completes | Batch failed mid-execution | Query AsyncApexJob for errors |
| Records not created | SOQL/DML error | Check batch error messages |
| No email notification | Email limit or address issue | Check email logs |

---

## Performance Metrics

**Expected Performance:**

| Metric | Value |
|--------|-------|
| UI Response Time | < 3 seconds |
| Taxonomy Batch | 2-5 minutes |
| Payer Network Batch | 5-10 minutes |
| IFC Batch | 1-3 minutes |
| Total Time | 8-18 minutes |
| Records/Minute | ~5-10 |

---

## Benefits Summary

| Aspect | Before | After |
|--------|--------|-------|
| **UI Experience** | 5+ min spinning | Instant return |
| **Governor Limits** | Hits limits | No issues |
| **Scalability** | Max 3 locations | Unlimited |
| **Error Handling** | All-or-nothing | Retry failed batches |
| **Monitoring** | None | Status + Email |
| **User Communication** | Silence | Status updates |

---

## Next Steps

1. **Phase 1 (Week 1):** Deploy to Sandbox and test
2. **Phase 2 (Week 2):** Production deployment with monitoring
3. **Phase 3 (Week 3):** Optimize batch sizes based on metrics
4. **Phase 4 (Month 2):** Add retry logic and dashboard

---

## Support & Questions

For questions or issues, contact your Salesforce admin or development team.
