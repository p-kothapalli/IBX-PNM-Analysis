# PRM Network Creation - Rollback Strategies for Multi-Batch Architecture

## Problem Statement

With 3 sequential batches (Taxonomy → Payer Networks → IFC), if Batch 2 or 3 fails, how do we rollback records created by previous successful batches?

**Challenge:** Each batch is a separate transaction - standard `Database.Rollback()` won't work across batches.

---

## Rollback Options

### Option 1: Compensation Pattern (Delete on Failure) ⭐ RECOMMENDED

**Concept:** If a batch fails, trigger a cleanup batch to delete all records from the request.

**Implementation:**

```apex
public class PRM_NetworkCreationRollbackBatch implements Database.Batchable<SObject> {
    
    private String requestId;
    private String caseManagerId;
    
    public PRM_NetworkCreationRollbackBatch(String requestId, String caseManagerId) {
        this.requestId = requestId;
        this.caseManagerId = caseManagerId;
    }
    
    public Database.QueryLocator start(Database.BatchableContext BC) {
        // Query all network records created for this request
        // Using a custom Request_Id__c field on each record
        return Database.getQueryLocator([
            SELECT Id FROM PRM_FacilityPractitionerTxNw__c 
            WHERE PRM_RequestId__c = :requestId
            UNION ALL
            SELECT Id FROM PRM_FacilityPractitionerNw__c
            WHERE PRM_RequestId__c = :requestId
            UNION ALL
            SELECT Id FROM PRM_FacilityIFC__c
            WHERE PRM_RequestId__c = :requestId
        ]);
    }
    
    public void execute(Database.BatchableContext BC, List<SObject> scope) {
        delete scope;
    }
    
    public void finish(Database.BatchableContext BC) {
        // Update status to "Rolled Back"
        updateStatus(caseManagerId, 'Rolled Back', 'Failed during processing. All changes reverted.');
        sendFailureNotification(caseManagerId, requestId);
    }
}
```

**Modify Batch Finish Methods:**

```apex
// In PRM_PayerNetworkBatch.finish()
public void finish(Database.BatchableContext BC) {
    if (totalErrors > 0 && totalProcessed == 0) {
        // Complete failure - rollback
        updateStatus('Rolling Back', 'Payer Network batch failed. Rolling back changes...');
        Database.executeBatch(new PRM_NetworkCreationRollbackBatch(requestId, caseManagerId), 200);
    } else if (totalErrors == 0) {
        // Success - continue to IFC batch
        Database.executeBatch(new PRM_IFCRecordBatch(params), 5);
    } else {
        // Partial success - decision needed (rollback or continue?)
        updateStatus('Partial Failure', 'Some records failed. Review required.');
    }
}
```

**Requirements:**
- Add `PRM_RequestId__c` field to all 3 objects (Taxonomy, Payer Network, IFC)
- Track requestId in all created records
- Create rollback batch class

**Pros:**
- ✅ Clean rollback - removes all related records
- ✅ Simple to understand and implement
- ✅ Works with existing data model

**Cons:**
- ❌ Temporary data exists before cleanup
- ❌ Requires tracking field on all objects
- ❌ Audit trail shows created then deleted records

---

### Option 2: Status-Based Activation (Pending → Active)

**Concept:** Create all records with `Status = 'Pending'`. Only activate them when all batches succeed.

**Implementation:**

```apex
// Modify batch classes to create records as "Pending"
private PRM_FacilityPractitionerTxNw__c createTaxonomyRecord(...) {
    return new PRM_FacilityPractitionerTxNw__c(
        // ... other fields
        PRM_Status__c = 'Pending',
        PRM_RequestId__c = requestId,
        PRM_IsActive__c = false  // Not active yet
    );
}

// Add final activation batch
public class PRM_NetworkActivationBatch implements Database.Batchable<SObject> {
    
    private String requestId;
    
    public Database.QueryLocator start(Database.BatchableContext BC) {
        return Database.getQueryLocator([
            SELECT Id, PRM_Status__c, PRM_IsActive__c
            FROM PRM_FacilityPractitionerTxNw__c
            WHERE PRM_RequestId__c = :requestId
            AND PRM_Status__c = 'Pending'
        ]);
        // Similar for other objects
    }
    
    public void execute(Database.BatchableContext BC, List<SObject> scope) {
        for (SObject record : scope) {
            record.put('PRM_Status__c', 'Active');
            record.put('PRM_IsActive__c', true);
        }
        update scope;
    }
}

// Modify IFC batch finish
public void finish(Database.BatchableContext BC) {
    if (totalErrors == 0) {
        // All batches succeeded - activate all records
        Database.executeBatch(new PRM_NetworkActivationBatch(requestId), 200);
    } else {
        // Failure - delete pending records
        Database.executeBatch(new PRM_NetworkCreationRollbackBatch(requestId, caseManagerId), 200);
    }
}
```

**Requirements:**
- Add `PRM_Status__c` field (Picklist: Pending, Active, Rolled Back)
- Add `PRM_RequestId__c` field
- Create activation batch
- Update queries to filter `Status = 'Active'` in production code

**Pros:**
- ✅ Records never "active" until full success
- ✅ Clear separation between pending and active
- ✅ Easy to query "what's pending"
- ✅ Rollback = delete pending records

**Cons:**
- ❌ Requires status field on all objects
- ❌ Downstream processes must filter by status
- ❌ More complex queries

---

### Option 3: Staging Table Pattern

**Concept:** Create records in staging tables first. Move to production tables only on full success.

**Implementation:**

```apex
// Create staging objects
PRM_StagingTaxonomyNetwork__c
PRM_StagingPayerNetwork__c
PRM_StagingIFC__c

// Batches create records in staging tables
public void execute(Database.BatchableContext BC, List<SObject> scope) {
    List<PRM_StagingTaxonomyNetwork__c> stagingRecords = new List<PRM_StagingTaxonomyNetwork__c>();
    
    for (...) {
        stagingRecords.add(new PRM_StagingTaxonomyNetwork__c(
            PRM_RequestId__c = requestId,
            PRM_CaseManagerId__c = caseManagerId,
            // ... all field values
        ));
    }
    insert stagingRecords;
}

// Final promotion batch (after IFC completes)
public class PRM_NetworkPromotionBatch implements Database.Batchable<SObject> {
    
    public void execute(Database.BatchableContext BC, List<SObject> scope) {
        // Convert staging records to production records
        List<PRM_FacilityPractitionerTxNw__c> prodRecords = new List<PRM_FacilityPractitionerTxNw__c>();
        
        for (PRM_StagingTaxonomyNetwork__c staging : (List<PRM_StagingTaxonomyNetwork__c>)scope) {
            prodRecords.add(new PRM_FacilityPractitionerTxNw__c(
                PRM_CaseManager__c = staging.PRM_CaseManagerId__c,
                // ... map all fields
            ));
        }
        
        insert prodRecords;
        delete scope; // Clean up staging
    }
}

// On failure - just delete staging records
public void finish(Database.BatchableContext BC) {
    if (totalErrors > 0) {
        // Delete all staging records for this request
        delete [SELECT Id FROM PRM_StagingTaxonomyNetwork__c WHERE PRM_RequestId__c = :requestId];
        delete [SELECT Id FROM PRM_StagingPayerNetwork__c WHERE PRM_RequestId__c = :requestId];
        delete [SELECT Id FROM PRM_StagingIFC__c WHERE PRM_RequestId__c = :requestId];
    }
}
```

**Requirements:**
- Create 3 staging custom objects (mirrors of production)
- Create promotion batch
- Cleanup logic for staging tables

**Pros:**
- ✅ True isolation - production untouched until success
- ✅ No impact on production queries
- ✅ Can review staging data before promotion
- ✅ Simple rollback - just delete staging

**Cons:**
- ❌ Requires duplicate object definitions
- ❌ More development effort
- ❌ Extra storage for staging data
- ❌ Additional data mapping logic

---

### Option 4: Transactional Wrapper with Bulk Processing ⚡

**Concept:** Don't split into 3 batches. Process all records in a single batch with smart chunking.

**Implementation:**

```apex
public class PRM_NetworkCreationBatch implements Database.Batchable<SObject>, Database.Stateful {
    
    // Store all records to create
    private Map<String, List<SObject>> recordsToCreate = new Map<String, List<SObject>>{
        'Taxonomy' => new List<SObject>(),
        'PayerNetwork' => new List<SObject>(),
        'IFC' => new List<SObject>()
    };
    
    public void execute(Database.BatchableContext BC, List<SObject> scope) {
        // Prepare all records (don't insert yet)
        for (SObject record : scope) {
            recordsToCreate.get('Taxonomy').add(createTaxonomyRecords(...));
            recordsToCreate.get('PayerNetwork').add(createPayerNetworkRecords(...));
            recordsToCreate.get('IFC').add(createIFCRecords(...));
        }
    }
    
    public void finish(Database.BatchableContext BC) {
        // All-or-nothing insert
        Savepoint sp = Database.setSavepoint();
        
        try {
            insert recordsToCreate.get('Taxonomy');
            insert recordsToCreate.get('PayerNetwork');
            insert recordsToCreate.get('IFC');
            
            updateStatus('Completed', null);
            
        } catch (Exception e) {
            // Rollback everything
            Database.rollback(sp);
            updateStatus('Failed', e.getMessage());
            throw e; // Let platform handle retry
        }
    }
}
```

**Requirements:**
- Careful memory management (stateful variables)
- Single batch design

**Pros:**
- ✅ True transaction - automatic rollback on failure
- ✅ No tracking fields needed
- ✅ Simple rollback mechanism

**Cons:**
- ❌ Heap size limits (12MB in finish method)
- ❌ All 54+ records in memory at once
- ❌ May still hit governor limits
- ❌ Can't process truly large volumes

---

### Option 5: Database Transaction Control with Custom Metadata

**Concept:** Track batch execution state. Use custom metadata or custom object to coordinate rollback.

**Implementation:**

```apex
// Custom Object: PRM_BatchExecutionLog__c
// Fields: RequestId__c, BatchName__c, Status__c, RecordsCreated__c, Timestamp__c

public class PRM_TaxonomyNetworkBatch ... {
    
    public void finish(Database.BatchableContext BC) {
        // Log successful completion
        insert new PRM_BatchExecutionLog__c(
            PRM_RequestId__c = requestId,
            PRM_BatchName__c = 'Taxonomy',
            PRM_Status__c = 'Completed',
            PRM_RecordsCreated__c = totalProcessed,
            PRM_Timestamp__c = Datetime.now()
        );
        
        if (totalErrors == 0) {
            // Continue to next batch
            Database.executeBatch(new PRM_PayerNetworkBatch(params), 2);
        } else {
            // Trigger rollback based on logs
            triggerRollback(requestId);
        }
    }
}

public static void triggerRollback(String requestId) {
    // Query what batches completed
    List<PRM_BatchExecutionLog__c> completedBatches = [
        SELECT PRM_BatchName__c
        FROM PRM_BatchExecutionLog__c
        WHERE PRM_RequestId__c = :requestId
        AND PRM_Status__c = 'Completed'
    ];
    
    // Delete records from completed batches
    for (PRM_BatchExecutionLog__c log : completedBatches) {
        if (log.PRM_BatchName__c == 'Taxonomy') {
            delete [SELECT Id FROM PRM_FacilityPractitionerTxNw__c 
                    WHERE PRM_RequestId__c = :requestId];
        }
        if (log.PRM_BatchName__c == 'PayerNetwork') {
            delete [SELECT Id FROM PRM_FacilityPractitionerNw__c 
                    WHERE PRM_RequestId__c = :requestId];
        }
    }
    
    // Update logs to "Rolled Back"
    for (PRM_BatchExecutionLog__c log : completedBatches) {
        log.PRM_Status__c = 'Rolled Back';
    }
    update completedBatches;
}
```

**Requirements:**
- Create `PRM_BatchExecutionLog__c` object
- Add logging to all batches
- Centralized rollback logic

**Pros:**
- ✅ Clear audit trail of batch execution
- ✅ Can replay/debug issues
- ✅ Flexible rollback logic
- ✅ Historical tracking

**Cons:**
- ❌ Extra logging overhead
- ❌ More code to maintain
- ❌ Requires additional object

---

### Option 6: Platform Events for Rollback Orchestration

**Concept:** Fire a "Rollback Requested" platform event. Trigger handles cleanup.

**Implementation:**

```apex
// Platform Event: NetworkCreationRollback__e
// Fields: RequestId__c, FailedBatchName__c, ErrorMessage__c

// In batch finish method
public void finish(Database.BatchableContext BC) {
    if (totalErrors > 0 && totalProcessed == 0) {
        // Publish rollback event
        NetworkCreationRollback__e rollbackEvent = new NetworkCreationRollback__e(
            RequestId__c = requestId,
            FailedBatchName__c = 'PayerNetwork',
            ErrorMessage__c = String.join(errorMessages, '\n')
        );
        EventBus.publish(rollbackEvent);
    }
}

// Trigger on rollback event
trigger NetworkCreationRollbackTrigger on NetworkCreationRollback__e (after insert) {
    for (NetworkCreationRollback__e event : Trigger.new) {
        PRM_RollbackOrchestrator.handleRollback(
            event.RequestId__c,
            event.FailedBatchName__c
        );
    }
}

// Orchestrator
public class PRM_RollbackOrchestrator {
    public static void handleRollback(String requestId, String failedBatch) {
        // Start rollback batch
        Database.executeBatch(
            new PRM_NetworkCreationRollbackBatch(requestId, caseManagerId),
            200
        );
    }
}
```

**Requirements:**
- Create rollback platform event
- Create trigger
- Orchestrator class

**Pros:**
- ✅ Decoupled architecture
- ✅ Async rollback handling
- ✅ Event-driven pattern
- ✅ Can add subscribers for notifications

**Cons:**
- ❌ More components to manage
- ❌ Platform event delivery (at-least-once, may duplicate)
- ❌ Debugging complexity

---

## Comparison Matrix

| Option | Complexity | Rollback Speed | Data Safety | Development Effort | Recommended For |
|--------|------------|----------------|-------------|-------------------|-----------------|
| **1. Compensation (Delete)** | Low | Fast | Good | Low | ⭐ Most projects |
| **2. Status-Based** | Medium | Medium | Excellent | Medium | High-compliance needs |
| **3. Staging Tables** | High | Slow | Excellent | High | Mission-critical |
| **4. Single Batch** | Medium | Instant | Excellent | Low | Small data volumes |
| **5. Transaction Log** | Medium | Fast | Good | Medium | Audit requirements |
| **6. Platform Events** | Medium | Fast | Good | Medium | Event-driven systems |

---

## Recommended Approach

### **Hybrid: Option 1 (Compensation) + Option 2 (Status)**

**Implementation:**

1. Add fields to all objects:
   - `PRM_RequestId__c` (Text, External ID)
   - `PRM_Status__c` (Picklist: Pending, Active, Failed, Rolled Back)
   - `PRM_IsActive__c` (Checkbox - only true when Active)

2. Create records with `Status = 'Pending'`

3. On full success (IFC batch completes):
   - Update all records: `Status = 'Active'`, `IsActive = true`

4. On failure (any batch fails):
   - Run rollback batch: Delete all records with `RequestId = X`
   - Update Case Manager: `Status = 'Rolled Back'`

5. Downstream queries always filter: `WHERE PRM_IsActive__c = true`

**Why This Works:**
- ✅ Records never "live" until full success
- ✅ Simple rollback (just delete)
- ✅ Clear audit trail (status field)
- ✅ Protects downstream processes (IsActive filter)
- ✅ Low development effort

---

## Code Changes Required

### Add Fields to Objects

**PRM_FacilityPractitionerTxNw__c:**
**PRM_FacilityPractitionerNw__c:**
**PRM_FacilityIFC__c:**

```xml
<fields>
    <fullName>PRM_RequestId__c</fullName>
    <externalId>true</externalId>
    <label>Request ID</label>
    <length>36</length>
    <required>false</required>
    <type>Text</type>
</fields>

<fields>
    <fullName>PRM_Status__c</fullName>
    <label>Status</label>
    <required>false</required>
    <type>Picklist</type>
    <valueSet>
        <restricted>true</restricted>
        <valueSetDefinition>
            <value>
                <fullName>Pending</fullName>
                <default>true</default>
            </value>
            <value>
                <fullName>Active</fullName>
            </value>
            <value>
                <fullName>Failed</fullName>
            </value>
            <value>
                <fullName>Rolled Back</fullName>
            </value>
        </valueSetDefinition>
    </valueSet>
</fields>

<fields>
    <fullName>PRM_IsActive__c</fullName>
    <defaultValue>false</defaultValue>
    <label>Is Active</label>
    <type>Checkbox</type>
</fields>
```

### Update Batch Classes

```apex
// Add to all record creation
private PRM_FacilityPractitionerTxNw__c createTaxonomyRecord(...) {
    return new PRM_FacilityPractitionerTxNw__c(
        // ... existing fields
        PRM_RequestId__c = requestId,
        PRM_Status__c = 'Pending',
        PRM_IsActive__c = false
    );
}
```

### Create Activation Batch

```apex
public class PRM_NetworkActivationBatch implements Database.Batchable<SObject> {
    private String requestId;
    
    public PRM_NetworkActivationBatch(String requestId) {
        this.requestId = requestId;
    }
    
    public Database.QueryLocator start(Database.BatchableContext BC) {
        // Query all pending records for this request across all 3 objects
        // Note: Can't UNION in QueryLocator, so need to handle separately
        return Database.getQueryLocator([
            SELECT Id, PRM_Status__c, PRM_IsActive__c
            FROM PRM_FacilityPractitionerTxNw__c
            WHERE PRM_RequestId__c = :requestId
            AND PRM_Status__c = 'Pending'
        ]);
    }
    
    public void execute(Database.BatchableContext BC, List<SObject> scope) {
        for (SObject record : scope) {
            record.put('PRM_Status__c', 'Active');
            record.put('PRM_IsActive__c', true);
        }
        update scope;
    }
    
    public void finish(Database.BatchableContext BC) {
        // Activate Payer Networks
        activatePayerNetworks();
    }
    
    private void activatePayerNetworks() {
        // Chain to activate other object types
        Database.executeBatch(new PRM_PayerNetworkActivationBatch(requestId), 200);
    }
}
```

### Create Rollback Batch

```apex
public class PRM_NetworkCreationRollbackBatch implements Database.Batchable<String>, Database.Stateful {
    
    private String requestId;
    private String caseManagerId;
    private List<String> objectsToClean = new List<String>{
        'PRM_FacilityPractitionerTxNw__c',
        'PRM_FacilityPractitionerNw__c',
        'PRM_FacilityIFC__c'
    };
    private Integer currentIndex = 0;
    
    public PRM_NetworkCreationRollbackBatch(String requestId, String caseManagerId) {
        this.requestId = requestId;
        this.caseManagerId = caseManagerId;
    }
    
    public Iterable<String> start(Database.BatchableContext BC) {
        return objectsToClean;
    }
    
    public void execute(Database.BatchableContext BC, List<String> scope) {
        for (String objectName : scope) {
            String query = 'SELECT Id FROM ' + objectName + 
                          ' WHERE PRM_RequestId__c = :requestId';
            List<SObject> recordsToDelete = Database.query(query);
            
            if (!recordsToDelete.isEmpty()) {
                delete recordsToDelete;
            }
        }
    }
    
    public void finish(Database.BatchableContext BC) {
        // Update Case Manager status
        update new CaseManager__c(
            Id = caseManagerId,
            PRM_NetworkCreationStatus__c = 'Rolled Back',
            PRM_NetworkCreationError__c = 'Network creation failed. All changes have been rolled back.'
        );
        
        // Send notification
        sendRollbackNotification(caseManagerId, requestId);
    }
}
```

### Update IFC Batch Finish Method

```apex
public void finish(Database.BatchableContext BC) {
    if (totalErrors == 0) {
        // All batches succeeded - activate all records
        updateStatus('Activating Records', null);
        Database.executeBatch(new PRM_NetworkActivationBatch(requestId), 200);
    } else {
        // Failure - rollback all records
        updateStatus('Rolling Back', 'IFC batch failed. Rolling back all changes...');
        Database.executeBatch(new PRM_NetworkCreationRollbackBatch(requestId, caseManagerId), 200);
    }
}
```

---

## Testing Rollback

### Unit Test Example

```apex
@isTest
static void testRollbackOnFailure() {
    // Setup test data
    CaseManager__c cm = createTestCaseManager();
    String requestId = 'TEST-ROLLBACK-001';
    
    // Create some taxonomy records (simulating successful Batch 1)
    List<PRM_FacilityPractitionerTxNw__c> taxonomyRecords = new List<PRM_FacilityPractitionerTxNw__c>();
    for (Integer i = 0; i < 5; i++) {
        taxonomyRecords.add(new PRM_FacilityPractitionerTxNw__c(
            PRM_RequestId__c = requestId,
            PRM_Status__c = 'Pending',
            PRM_IsActive__c = false,
            PRM_CaseManager__c = cm.Id
        ));
    }
    insert taxonomyRecords;
    
    // Verify records exist
    System.assertEquals(5, [SELECT COUNT() FROM PRM_FacilityPractitionerTxNw__c 
                            WHERE PRM_RequestId__c = :requestId]);
    
    Test.startTest();
    // Trigger rollback
    PRM_NetworkCreationRollbackBatch rollback = 
        new PRM_NetworkCreationRollbackBatch(requestId, cm.Id);
    Database.executeBatch(rollback);
    Test.stopTest();
    
    // Verify all records deleted
    System.assertEquals(0, [SELECT COUNT() FROM PRM_FacilityPractitionerTxNw__c 
                            WHERE PRM_RequestId__c = :requestId]);
    
    // Verify status updated
    cm = [SELECT PRM_NetworkCreationStatus__c FROM CaseManager__c WHERE Id = :cm.Id];
    System.assertEquals('Rolled Back', cm.PRM_NetworkCreationStatus__c);
}
```

---

## Decision Matrix

| Scenario | Recommended Option |
|----------|-------------------|
| **Small volume (< 20 records total)** | Option 4 (Single Batch) |
| **Medium volume (20-100 records)** | Option 1 + 2 (Hybrid) ⭐ |
| **Large volume (100+ records)** | Option 3 (Staging Tables) |
| **Strict compliance/audit** | Option 2 (Status-Based) |
| **Existing event architecture** | Option 6 (Platform Events) |
| **Quick implementation** | Option 1 (Compensation) |

---

## Summary

**For your use case (3 locations, 54 records):**

✅ **Use Hybrid Approach (Option 1 + 2)**

**Implementation Steps:**
1. Add 3 fields to all objects (RequestId, Status, IsActive)
2. Modify batches to create records as "Pending"
3. Create activation batch (runs after IFC completes)
4. Create rollback batch (runs on any failure)
5. Update finish methods to trigger activation or rollback
6. Update downstream queries to filter `IsActive = true`

**Rollback Flow:**
```
Batch Fails
  → Status = "Rolling Back"
  → Delete all records WHERE RequestId = X
  → Status = "Rolled Back"
  → Send notification
```

**Time to Rollback:** 30-60 seconds (delete ~54 records)

**Data Safety:** High (records never "live" until full success)
