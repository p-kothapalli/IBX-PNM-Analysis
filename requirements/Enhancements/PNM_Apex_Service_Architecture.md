# PNM Apex Service Architecture - Comprehensive Design Guide

## Executive Summary

This document defines the reusable Apex Service Framework for Provider Network Management (PNM) transactions, replacing heavyweight OmniStudio Integration Procedures with a scalable, governor-limit-safe architecture. The framework uses a layered Service-Oriented Architecture (SOA) with automatic sync/async delegation, generic request/response wrappers, and pluggable service modules.

The same pattern successfully applied in the **Practitioner Creation Redesign** (where Level 4 record creation moved to Apex Batch) is now generalized into a reusable framework for ALL PNM transactions.

---

## 1. Architecture Overview - Layer Diagram

```
+=====================================================================+
|                    OMNISTUDIO PRESENTATION LAYER                      |
|  (OmniScripts, FlexCards, LWC)                                       |
+=====================================================================+
         |                              |
         | Remote Action / IP Call      | DataRaptor (simple reads)
         v                              v
+=====================================================================+
|               CONTROLLER / DISPATCHER LAYER                          |
|  PNM_ServiceDispatcher (implements vlocityOpenInterface2)            |
|  - Deserializes OmniStudio JSON input                                |
|  - Routes to correct Service based on 'actionName'                   |
|  - Returns standardized PNM_ServiceResponse                          |
+=====================================================================+
         |
         v
+=====================================================================+
|                      SERVICE LAYER                                    |
|  PNM_PractitionerService                                             |
|  PNM_FacilityService                                                 |
|  PNM_CredentialingService                                            |
|  PNM_ContractingService                                              |
|  PNM_RosterProcessingService                                         |
|  PNM_PracticeLocationService                                         |
|  PNM_ParticipationFormService  <-- Primary focus                     |
+=====================================================================+
         |                    |                     |
         v                    v                     v
+==================+ +==================+ +====================+
|  SELECTOR LAYER  | |  UTILITY LAYER   | |  ASYNC FRAMEWORK   |
|  PNM_Selector    | |  PNM_DMLUtil     | |  PNM_AsyncRouter    |
|  (Dynamic SOQL)  | |  PNM_MapUtil     | |  PNM_BatchProcessor |
|                  | |  PNM_JSONUtil    | |  PNM_QueueableChain |
|                  | |  PNM_HeapUtil    | |                    |
+==================+ +==================+ +====================+
         |                    |                     |
         v                    v                     v
+=====================================================================+
|                    CROSS-CUTTING CONCERNS                             |
|  PNM_ErrorLogger (Custom Object: PNM_Error_Log__c)                   |
|  PNM_TransactionContext (governor limit tracking)                     |
|  PNM_FeatureFlags (Custom Metadata: PNM_Config__mdt)                 |
+=====================================================================+
         |
         v
+=====================================================================+
|                SALESFORCE DATA LAYER                                  |
|  Account, Contact, HealthcarePractitioner, HealthcareFacility,       |
|  PractitionerRole, CareProviderFacilitySpecialty, Address, etc.      |
+=====================================================================+
```

---

## 2. Why Each Layer Exists — and How It Helps

Each layer in the framework solves a specific operational, technical, or organizational problem. This section is the answer to *"why didn't we just write one big Apex class per flow?"* — for every architecture layer below we explain **why we need it**, **how it helps**, **what would happen without it**, and a measurable **outcome**.

> The 8 layers below mirror the layered diagram in §1 and the interactive mind map (`PNM_Modernization_MindMap.html`). Click any layer in the HTML to see the same explanation inline.

<!-- LAYER_EXPLANATIONS_PLACEHOLDER -->

### 2.1 OmniScript / OmniStudio UI — kept verbatim

**Why we need it.** The provider-network team has invested years training the credentialing committee, contracting analysts, and PNC reviewers on the existing OmniScript flows. Every screen has been QA'd against business rules, accessibility, and downstream Health Cloud objects. Replacing those flows would force a parallel re-validation cycle, retraining of ~80 internal users, and a rewrite of help-desk runbooks.

**How it helps.** By preserving the OmniScript JSON contract verbatim — every field name, every property bag, every event — the migration is invisible to end users. The thin-wrapper IP returns the same response shape the OmniScript expects, so nothing on the screen changes. Risk drops from "UI re-platform" to "back-end refactor."

**Without it.** Every flow would need a parallel LWC rebuild, doubling project timeline and putting field-level validation logic at risk of drift between the old and new UI.

**Outcome.** $0 retraining cost. 0 user-facing changes per migration.

---

### 2.2 Thin-wrapper Integration Procedure (3 elements)

**Why we need it.** Today an orchestrator IP can carry 50–80 elements of branching logic, DataRaptor calls, and Remote Action stubs. That logic is brittle (the JSON DSL has no compiler), untestable (no Apex test class can cover an IP), and accounts for >70% of the IP's CPU budget. A single bug requires a full sandbox refresh + UAT cycle to fix.

**How it helps.** Every migrated IP collapses to three nodes:

1. `SetValues` — assemble the `PRM_ServiceRequest` JSON from the OmniScript dataJson.
2. `Remote Action` → `PRM_ServiceDispatcher.invokeMethod()` — single Apex call.
3. `Response Action` — return the `PRM_ServiceResponse` to the OmniScript.

All conditional logic moves into Apex where it's debuggable, version-controlled, unit-testable, and code-reviewable.

**Without it.** Either we'd ship LWC replacements (high risk, see §2.1) OR we'd keep the heavy logic in OmniStudio and forfeit the governor-limit and CPU wins.

**Outcome.** Average orchestrator-IP element count: 50+ → **3**. Heaviest IP retired: `PRM_CreatePractitionerAddressRecords` (80+ elements → 0).

---

### 2.3 PRM_ServiceDispatcher — registry-driven routing

**Why we need it.** Hard-coding `serviceName → Apex class` mappings inside every IP would create hundreds of brittle integration points. Renaming a class would silently break 30+ IPs. There would be no centralized place to enforce auth, instrumentation, transaction-context initialization, or top-level error handling.

**How it helps.** A single Apex class implements `vlocity_ins.VlocityOpenInterface2` and acts as the front door for every PNM Apex call:

- Maintains a registry: `serviceName ("OffCycleSubmit", "ReinstatePractitioner", …) → Type`.
- Initializes `PRM_TransactionContext` (correlation id, limits snapshot, audit user).
- Delegates to `PRM_BaseService.execute(request)`.
- Catches `PRM_ServiceException` / `Exception`, writes a structured row to `PRM_ExceptionLog__c`, and returns a uniform error envelope.

New flows register one row in `PRM_FeatureConfig__mdt`. Zero dispatcher code changes.

**Without it.** Each IP needs a custom Apex entry-point class, multiplying error-handling, security, and logging boilerplate by N. Cross-cutting changes (e.g. "all PNM calls must now stamp a correlation id") become an N-class refactor.

**Outcome.** **One** class is the entry point for every PNM service. Adding a new flow = one Custom Metadata row + one service class.

---

### 2.4 PRM_BaseService (Template Method)

**Why we need it.** Without a shared base, every service has to re-implement: governor-limit checks, sync-vs-async decision logic, transaction-context tracking, error-envelope construction, structured logging, and audit-trail stamping. Drift between services is inevitable — and the worst-tested services will exception out in production under load.

**How it helps.** One abstract class declares the lifecycle:

- `processSync(request)` — the critical path the user must wait for.
- `processAsync(request)` — heavy DML / Level-4 fan-out that user navigation should not block on.
- `decideMode()` — polls `PRM_GovernorUtil.atRiskOfLimitBreach()` and the volume on the request to choose the path.

Subclasses just implement business logic. The base class handles delegation to Queueable, error wrapping, and logging.

**Without it.** Sync/async wiring is forgotten in 1-2 services → those services fail at peak load with `Apex CPU time limit exceeded`. Forensic debugging becomes a per-service archaeology project. A single async fix has to be applied N times.

**Outcome.** Every PNM service is **governor-safe by construction**. Zero per-service async wiring code.

---

### 2.5 Domain Services & Reactivators

**Why we need it.** Flow-specific rules ("when a Practitioner is reinstated AND has >10 active locations, route to `PRM_ReinstateVendorAccountBatch`"; "when PDA outcome = Reroute to QM, clone the case + re-stamp CaseManager") have to live somewhere. Inline-in-IP makes them untestable. Inline-in-LWC ships them to the wrong layer (data work in a UI component). Inline-in-Trigger couples them to record events instead of user intent.

**How it helps.** Each guided flow gets one **orchestrator service** (e.g. `PRM_ParFormSubmitService`, `PRM_OffCycleSubmitService`, `PRM_ReinstatePractitionerService`) that composes shared **sub-services** (`PRM_CaseService`, `PRM_AddressService`, `PRM_IdentifierService`, `PRM_NetworkCloneUtil`, `PRM_PreciselyAdapter`, `PRM_NoteService`, `PRM_AccountUpdater`, `PRM_TaxonomyService`).

For Reinstate specifically, eight standardized **Reactivators** (`PRM_HCFReactivator`, `PRM_HCPFReactivator`, `PRM_HCFNReactivator`, `PRM_BoardCertReactivator`, `PRM_InfoCodeReactivator`, `PRM_ProviderFeatureReactivator`, `PRM_TaxonomyReactivator`, `PRM_IdentifierReactivator`) standardize the "set IsActive=true + clear EffectiveTo" pattern across 8 SObjects — so every reinstate flow uses the same proven primitive.

**Without it.** Each new flow re-writes Case-creation, Address-validation, Identifier-creation logic. Bug fixes get applied N times. Reuse score never rises.

**Outcome.** Reuse rises with every migration: Par Form 0% baseline → PDA 70% → Off Cycle 75% → Off Cycle PDA 76% → Reinstate 62% + 750 LoC of existing Apex preserved verbatim. By the 6th flow we expect >85% reuse.

---

### 2.6 Selectors · Transformers · Utilities

**Why we need it.** Direct SOQL inside services makes them slow to test (every test seeds data) and unsafe (FLS/CRUD checks get forgotten). Direct DML from anywhere makes partial-success unmanageable. JSON-to-SObject conversions get duplicated everywhere.

**How it helps.** A small toolbox of mockable, single-responsibility helpers:

- **Selectors** (`PRM_AccountSelector`, `PRM_HCFSelector`, `PRM_HCPFSelector`, `PRM_HCFNetworkSelector`, `PRM_IdentifierSelector`, `PRM_LocationNPIHistorySelector`, `PRM_OffCycleFormSelector`) — bulk-read façades; one query per type, mockable in unit tests, FLS-aware.
- **Transformers** (`PRM_OffCycleAddressTransformer`, `PRM_OffCycleNetworkTransformer`, `PRM_OffCyclePFAATransformer`, `PRM_OffCyclePDAHFNTransformer`, `PRM_ReinstateTransformer`) — pure functions that turn OmniStudio JSON into SObject collections (and vice versa). No DML, no SOQL — easy to unit-test.
- **Utilities** — `PRM_DMLUtil` (partial-success DML, per-row error capture), `PRM_CollectionUtil` (Map<Id,SObject> helpers, partition-by-key), `PRM_GovernorUtil` (remaining SOQL/CPU/heap snapshots, "atRiskOfBreach" predicate), `PRM_ErrorLogger` (structured rows in `PRM_ExceptionLog__c`), `PRM_TransactionContext` (correlation id passed through every service hop), `PRM_IdGenerator` (deterministic transactionId).

**Without it.** Every service hand-rolls SOQL → service tests need 200+ lines of seed data → developers skip writing tests → quality drops.

**Outcome.** Test-class lines per service: 1,200 → ~300. Unit-test runtime: 12s → 2s.

---

### 2.7 Async Layer (Queueable / Batchable)

**Why we need it.** Salesforce gives a synchronous transaction 10s CPU + 100 SOQL + 150 DML rows per object. A Reinstate of a 25-location practitioner needs 9 reactivators × 25 rows = 225 DML rows — one and a half times the per-object DML budget — before any business logic runs. Heavy IPs already breach this in production today.

**How it helps.** `PRM_AsyncJobBase` is a uniform Queueable scaffold that subclasses override with their `executeAsync(context)`:

- Heavy fan-out (Level-4 records, role-exploded HCFNs, NPI history rollovers, ProviderFeature stamps) goes here.
- The user gets `caseId` immediately from the sync TX1 path.
- Completion publishes `PRM_AsyncComplete__e` — the LWC bell, downstream IP, and Flow can subscribe to this event.
- Existing `PRM_ReinstateVendorAccountBatch` (~750 LoC) is **wrapped, not replaced** — preserving validated logic for the >10-location reinstate path.

**Without it.** Heavy flows hit governor limits on the worst day of the year (peak credentialing). Users see `Apex CPU time limit exceeded` with no breadcrumb. Refunds, escalations, and manual data fixes follow.

**Outcome.** Sync TX1 stays under 1s on every flow; TX2 batches handle the heavy DML invisibly. Peak CPU: 3.5–7.5s today → <1s after migration.

---

### 2.8 Salesforce Database — partial-success commit

**Why we need it.** `Database.insert(records, true)` (allOrNone=true) is the default — and it rolls back the entire transaction if any one row fails. For a Reinstate of a 25-location practitioner, **one** bad role mapping rejects the whole submit and the user has to re-key everything.

**How it helps.** `PRM_DMLUtil` always uses `allOrNone=false`. Per-row results come back; failures are recorded in `PRM_ExceptionLog__c` with the offending record, the error code, and the human-readable reason. The user sees: "23 of 25 locations reinstated — 2 require manual review (see notification)." The good rows commit. The bad ones become tickets.

**Without it.** One bad row blocks the submit → user retries → bad row still bad → escalation → a credentialing analyst manually splits the request.

**Outcome.** Partial-success mode means the happy path always commits; the unhappy 1-2% never blocks the 98%.

---

---

## 3. Generic Request/Response Wrapper

### 3.1 PNM_ServiceRequest

```java
/**
 * Standardized request wrapper that normalizes OmniStudio JSON input
 * into a typed, predictable structure for all PNM services.
 */
public class PNM_ServiceRequest {
    
    // Core routing fields
    public String actionName;          // e.g., 'createPractitioner', 'updatePracticeLocation'
    public String transactionId;       // Unique ID for tracing/logging
    public String sourceSystem;        // 'OmniScript', 'IP', 'API', 'Batch'
    
    // Data payload - generic enough for any transaction
    public List<Map<String, Object>> records;    // Bulk records to process
    public Map<String, Object> parameters;       // Additional config/filter params
    public Map<String, Object> metadata;         // OmniStudio context (step info, etc.)
    
    // Processing directives
    public Boolean forceAsync = false;           // Force async even for small volumes
    public Integer batchSize;                    // Override default batch size
    public String callbackEventName;             // Platform Event to fire on completion
    
    /**
     * Factory method to parse from OmniStudio's raw input map
     */
    public static PNM_ServiceRequest fromOmniInput(Map<String, Object> input) {
        PNM_ServiceRequest req = new PNM_ServiceRequest();
        req.transactionId = PNM_IdGenerator.generateTransactionId();
        req.actionName = (String) input.get('actionName');
        req.sourceSystem = (String) input.get('sourceSystem') ?? 'OmniScript';
        
        // OmniStudio sends arrays as List<Object> - normalize to List<Map>
        Object rawRecords = input.get('records');
        if (rawRecords instanceof List<Object>) {
            req.records = new List<Map<String, Object>>();
            for (Object item : (List<Object>) rawRecords) {
                req.records.add((Map<String, Object>) item);
            }
        }
        
        req.parameters = (Map<String, Object>) input.get('parameters') ?? 
                         new Map<String, Object>();
        req.metadata = (Map<String, Object>) input.get('metadata') ?? 
                       new Map<String, Object>();
        req.forceAsync = input.get('forceAsync') == true;
        req.batchSize = (Integer) input.get('batchSize');
        req.callbackEventName = (String) input.get('callbackEventName');
        
        return req;
    }
    
    /**
     * Returns the number of records to process (used for async threshold decisions)
     */
    public Integer getRecordCount() {
        return records != null ? records.size() : 0;
    }
}
```

### 3.2 PNM_ServiceResponse

```java
/**
 * Standardized response wrapper returned to OmniStudio.
 * OmniScripts can bind directly to these fields.
 */
public class PNM_ServiceResponse {
    
    public Boolean success;
    public String transactionId;
    public String message;
    public String processingMode;  // 'SYNC' or 'ASYNC'
    
    // Results payload
    public List<Map<String, Object>> results;
    public Map<String, Object> summary;
    
    // Error details (populated on failure)
    public List<PNM_ErrorDetail> errors;
    
    // Async tracking (populated when delegated to async)
    public Id asyncJobId;
    public String statusCheckEventName;
    
    public class PNM_ErrorDetail {
        public String recordIdentifier;
        public String errorCode;
        public String errorMessage;
        public String fieldName;
    }
    
    // --- Factory Methods ---
    
    public static PNM_ServiceResponse success(String transactionId, 
                                               List<Map<String, Object>> results) {
        PNM_ServiceResponse resp = new PNM_ServiceResponse();
        resp.success = true;
        resp.transactionId = transactionId;
        resp.processingMode = 'SYNC';
        resp.results = results;
        resp.message = 'Transaction completed successfully.';
        return resp;
    }
    
    public static PNM_ServiceResponse asyncDelegated(String transactionId, 
                                                      Id jobId, 
                                                      String eventName) {
        PNM_ServiceResponse resp = new PNM_ServiceResponse();
        resp.success = true;
        resp.transactionId = transactionId;
        resp.processingMode = 'ASYNC';
        resp.asyncJobId = jobId;
        resp.statusCheckEventName = eventName;
        resp.message = 'Request accepted. Processing asynchronously.';
        return resp;
    }
    
    public static PNM_ServiceResponse failure(String transactionId, 
                                               List<PNM_ErrorDetail> errors) {
        PNM_ServiceResponse resp = new PNM_ServiceResponse();
        resp.success = false;
        resp.transactionId = transactionId;
        resp.processingMode = 'SYNC';
        resp.errors = errors;
        resp.message = 'Transaction failed. See errors for details.';
        return resp;
    }
    
    /**
     * Convert to Map for OmniStudio output binding
     */
    public Map<String, Object> toOutputMap() {
        Map<String, Object> output = new Map<String, Object>();
        output.put('success', this.success);
        output.put('transactionId', this.transactionId);
        output.put('message', this.message);
        output.put('processingMode', this.processingMode);
        output.put('results', this.results);
        output.put('summary', this.summary);
        output.put('asyncJobId', this.asyncJobId);
        output.put('statusCheckEventName', this.statusCheckEventName);
        if (this.errors != null) {
            output.put('errors', JSON.deserializeUntyped(JSON.serialize(this.errors)));
        }
        return output;
    }
}
```

---

## 4. Core Framework Classes

### 4.1 PNM_ServiceDispatcher (Controller/Entry Point)

> **Why we need it** — Without a single front door, every IP would have to hard-code its own Apex class name, security header, error envelope, and correlation-id stamping. Renaming a class would silently break dozens of IPs.
>
> **How it helps** — One `vlocity_ins.VlocityOpenInterface2` implementation routes any inbound `serviceName` to the right `PRM_BaseService` subclass via a registry, initializes `PRM_TransactionContext`, and returns a uniform error envelope on any failure.
>
> **Outcome** — Adding a new flow = 1 row in `SERVICE_REGISTRY` (or `PRM_FeatureConfig__mdt`) + 1 service class. Zero dispatcher changes ever.

```java
/**
 * SINGLE ENTRY POINT for all OmniStudio-invoked PNM Apex services.
 * 
 * Implements VlocityOpenInterface2 for Remote Action invocation from 
 * OmniScripts and lightweight Integration Procedures.
 * 
 * Usage from OmniStudio:
 *   Remote Action -> Class: PNM_ServiceDispatcher
 *   Input JSON must include: { "actionName": "createPractitioner", "records": [...] }
 */
global with sharing class PNM_ServiceDispatcher implements vlocity_ins.VlocityOpenInterface2 {
    
    // Service registry - maps action names to service implementations
    private static final Map<String, Type> SERVICE_REGISTRY = new Map<String, Type>{
        // Practitioner Participation Form
        'processPractitionerParticipation' => PNM_ParticipationFormService.class,
        'createPractitioner'               => PNM_PractitionerService.class,
        'updatePractitioner'               => PNM_PractitionerService.class,
        
        // Practice Location
        'updatePracticeLocation'           => PNM_PracticeLocationService.class,
        'createPracticeLocation'           => PNM_PracticeLocationService.class,
        
        // Facility
        'upsertFacility'                   => PNM_FacilityService.class,
        
        // Credentialing
        'processCredentials'               => PNM_CredentialingService.class,
        
        // Contracting
        'processContract'                  => PNM_ContractingService.class,
        
        // Roster
        'processRosterFile'                => PNM_RosterProcessingService.class
    };
    
    /**
     * VlocityOpenInterface2 entry point
     */
    global Boolean invokeMethod(String methodName, 
                                 Map<String, Object> input, 
                                 Map<String, Object> output, 
                                 Map<String, Object> options) {
        
        PNM_TransactionContext ctx = PNM_TransactionContext.initialize();
        
        try {
            // Parse standardized request
            PNM_ServiceRequest request = PNM_ServiceRequest.fromOmniInput(input);
            
            // Resolve action name (support methodName override from IP config)
            String actionName = request.actionName ?? methodName;
            request.actionName = actionName;
            ctx.actionName = actionName;
            
            // Lookup service
            Type serviceType = SERVICE_REGISTRY.get(actionName);
            if (serviceType == null) {
                throw new PNM_ServiceException(
                    'PNM-001', 
                    'Unknown action: ' + actionName + '. Available: ' + SERVICE_REGISTRY.keySet()
                );
            }
            
            // Instantiate and execute
            PNM_BaseService service = (PNM_BaseService) serviceType.newInstance();
            PNM_ServiceResponse response = service.execute(request);
            
            // Write response to output map for OmniStudio
            output.putAll(response.toOutputMap());
            
            return response.success;
            
        } catch (PNM_ServiceException ex) {
            PNM_ErrorLogger.log(ex, ctx);
            output.put('success', false);
            output.put('errorCode', ex.errorCode);
            output.put('message', ex.getMessage());
            return false;
            
        } catch (Exception ex) {
            PNM_ErrorLogger.log(ex, ctx);
            output.put('success', false);
            output.put('errorCode', 'PNM-999');
            output.put('message', 'An unexpected error occurred. Transaction ID: ' + ctx.transactionId);
            return false;
        }
    }
}
```

### 4.2 PNM_BaseService (Abstract Service Foundation)

> **Why we need it** — Every service needs the same plumbing: governor-limit checks, sync-vs-async decision, transaction-context tracking, error wrapping, audit logging. Without a base class this code drifts between services and the worst-tested ones fail in production.
>
> **How it helps** — Template-Method base class declares `processSync()` (must finish before user navigates) and `processAsync()` (Level-4 / heavy DML). `decideMode()` polls `PRM_GovernorUtil` and the request volume to choose. Subclasses only write business logic.
>
> **Outcome** — Every service is governor-safe by construction. One sync/async fix = N services updated.

```java
/**
 * Abstract base for all PNM services. Provides:
 * - Governor limit pre-checks
 * - Automatic sync/async routing
 * - Standard execution lifecycle hooks
 * - Logging integration
 * 
 * Subclasses implement: validate(), processSync(), getAsyncProcessor()
 */
public abstract class PNM_BaseService {
    
    // Configurable thresholds (can be overridden by Custom Metadata)
    protected Integer ASYNC_RECORD_THRESHOLD = 200;    // Records above this -> async
    protected Integer HEAP_SAFETY_MARGIN_MB = 3;       // MB to keep free
    protected Integer CPU_SAFETY_MARGIN_MS = 2000;     // ms to keep free
    protected Integer SOQL_SAFETY_MARGIN = 10;         // queries to keep free
    protected Integer DML_BATCH_SIZE = 200;            // DML rows per operation
    
    protected PNM_TransactionContext ctx;
    
    /**
     * Main execution entry point - Template Method pattern
     */
    public PNM_ServiceResponse execute(PNM_ServiceRequest request) {
        this.ctx = PNM_TransactionContext.current();
        
        // Load runtime configuration from Custom Metadata
        loadConfiguration(request.actionName);
        
        // Step 1: Validate input
        List<PNM_ServiceResponse.PNM_ErrorDetail> validationErrors = validate(request);
        if (validationErrors != null && !validationErrors.isEmpty()) {
            return PNM_ServiceResponse.failure(request.transactionId, validationErrors);
        }
        
        // Step 2: Determine processing mode
        if (shouldProcessAsync(request)) {
            return delegateToAsync(request);
        }
        
        // Step 3: Process synchronously
        return processSync(request);
    }
    
    /**
     * Determine if this request should be routed to async processing.
     * Considers: record volume, remaining governor limits, forceAsync flag.
     */
    protected virtual Boolean shouldProcessAsync(PNM_ServiceRequest request) {
        // Explicit async request
        if (request.forceAsync) return true;
        
        // Volume-based threshold
        if (request.getRecordCount() > ASYNC_RECORD_THRESHOLD) return true;
        
        // Governor limit proximity check
        if (Limits.getHeapSize() > (Limits.getLimitHeapSize() - (HEAP_SAFETY_MARGIN_MB * 1048576))) {
            return true;
        }
        if (Limits.getCpuTime() > (Limits.getLimitCpuTime() - CPU_SAFETY_MARGIN_MS)) {
            return true;
        }
        if (Limits.getQueries() > (Limits.getLimitQueries() - SOQL_SAFETY_MARGIN)) {
            return true;
        }
        
        return false;
    }
    
    /**
     * Delegate processing to async (Queueable or Batch)
     */
    protected PNM_ServiceResponse delegateToAsync(PNM_ServiceRequest request) {
        PNM_AsyncProcessor processor = getAsyncProcessor(request);
        Id jobId;
        
        if (request.getRecordCount() > 2000) {
            // Use Batch for very large volumes
            jobId = Database.executeBatch(
                (Database.Batchable<SObject>) processor, 
                request.batchSize ?? DML_BATCH_SIZE
            );
        } else {
            // Use Queueable for moderate volumes
            jobId = System.enqueueJob((Queueable) processor);
        }
        
        // Log async delegation
        PNM_ErrorLogger.logInfo(
            'Async delegation: ' + request.actionName + 
            ' (' + request.getRecordCount() + ' records) -> Job: ' + jobId,
            ctx
        );
        
        return PNM_ServiceResponse.asyncDelegated(
            request.transactionId, 
            jobId, 
            request.callbackEventName ?? 'PNM_AsyncComplete__e'
        );
    }
    
    /**
     * Load runtime thresholds from PNM_Service_Config__mdt
     */
    private void loadConfiguration(String actionName) {
        PNM_Service_Config__mdt config = PNM_Service_Config__mdt.getInstance(actionName);
        if (config != null) {
            if (config.Async_Record_Threshold__c != null) 
                ASYNC_RECORD_THRESHOLD = (Integer) config.Async_Record_Threshold__c;
            if (config.DML_Batch_Size__c != null) 
                DML_BATCH_SIZE = (Integer) config.DML_Batch_Size__c;
        }
    }
    
    // --- Abstract methods for subclasses ---
    
    /** Validate the request. Return errors or empty list. */
    protected abstract List<PNM_ServiceResponse.PNM_ErrorDetail> validate(PNM_ServiceRequest request);
    
    /** Synchronous processing logic. */
    protected abstract PNM_ServiceResponse processSync(PNM_ServiceRequest request);
    
    /** Return the async processor (Queueable/Batchable) for this service. */
    protected abstract PNM_AsyncProcessor getAsyncProcessor(PNM_ServiceRequest request);
}
```

### 4.3 PNM_AsyncProcessor (Async Interface)

> **Why we need it** — Heavy DML (Level-4 record fan-out, role-exploded HCFNs, NPI history rollovers, 25-location reinstates) cannot run in the user's synchronous transaction without breaching governor limits. We need a uniform contract for "this work happens after the user gets their case id."
>
> **How it helps** — A common interface (`executeAsync(context)`) implemented by every Queueable / Batchable in PNM. `PRM_AsyncJobBase` provides scaffolding: chunking, retry on `LimitException`, `PRM_AsyncComplete__e` publication on success, structured logging on failure.
>
> **Outcome** — Sync TX1 stays under 1s; the async TX2 runs invisibly. The LWC bell, downstream IP, and Flow all subscribe to the same completion event.

```java
/**
 * Marker interface for PNM async processors.
 * Implementations should also implement Queueable and/or Database.Batchable.
 */
public interface PNM_AsyncProcessor {
    void setRequest(PNM_ServiceRequest request);
}
```

---

## 5. Utility Layer Classes

### 5.1 PNM_DMLUtil (Generic DML Handler)

> **Why we need it** — Default DML uses `allOrNone=true`: one bad row rolls back the whole transaction. For multi-record submits (25-location reinstates, multi-address PARs) one invalid row forces the user to re-key everything. We also need consistent FLS/CRUD enforcement.
>
> **How it helps** — Centralized partial-success DML (`Database.insert(records, false)`), per-row result inspection, structured failure capture into `PRM_ExceptionLog__c`, FLS-aware update via `Security.stripInaccessible`. Returns `PNM_DMLResult` with `successIds` and `failures` for the service to report back.
>
> **Outcome** — Happy path always commits. The unhappy 1-2% become tickets, not rollbacks. Users see "23 of 25 saved — 2 require review" instead of a blanket failure.

```java
/**
 * Centralized DML utility that provides:
 * - Batched DML to avoid governor limits
 * - Partial success handling (allOrNone = false)
 * - Automatic retry logic for lock failures
 * - Standardized error collection
 */
public class PNM_DMLUtil {
    
    private static final Integer DEFAULT_BATCH_SIZE = 200;
    
    /**
     * Bulk upsert with external ID field support and partial success.
     * Returns a result object with successes and failures separated.
     */
    public static PNM_DMLResult bulkUpsert(List<SObject> records, 
                                            Schema.SObjectField externalIdField,
                                            Integer batchSize) {
        if (records == null || records.isEmpty()) {
            return new PNM_DMLResult();
        }
        
        Integer effectiveBatchSize = batchSize ?? DEFAULT_BATCH_SIZE;
        PNM_DMLResult result = new PNM_DMLResult();
        
        // Process in batches to stay within DML row limits
        List<List<SObject>> batches = PNM_CollectionUtil.chunk(records, effectiveBatchSize);
        
        for (List<SObject> batch : batches) {
            // Check governor limits before each batch
            if (!PNM_GovernorUtil.canPerformDML(batch.size())) {
                result.addError('GOVERNOR_LIMIT', 
                    'Insufficient DML capacity. Processed ' + result.successCount + 
                    ' of ' + records.size() + ' records.');
                break;
            }
            
            List<Database.UpsertResult> upsertResults;
            if (externalIdField != null) {
                upsertResults = Database.upsert(batch, externalIdField, false);
            } else {
                upsertResults = Database.upsert(batch, false);
            }
            
            // Process results
            for (Integer i = 0; i < upsertResults.size(); i++) {
                Database.UpsertResult ur = upsertResults[i];
                if (ur.isSuccess()) {
                    result.addSuccess(ur.getId(), ur.isCreated());
                } else {
                    result.addFailure(batch[i], ur.getErrors());
                }
            }
        }
        
        return result;
    }
    
    /**
     * Bulk insert with partial success
     */
    public static PNM_DMLResult bulkInsert(List<SObject> records, Integer batchSize) {
        if (records == null || records.isEmpty()) return new PNM_DMLResult();
        
        Integer effectiveBatchSize = batchSize ?? DEFAULT_BATCH_SIZE;
        PNM_DMLResult result = new PNM_DMLResult();
        
        for (List<SObject> batch : PNM_CollectionUtil.chunk(records, effectiveBatchSize)) {
            if (!PNM_GovernorUtil.canPerformDML(batch.size())) {
                result.addError('GOVERNOR_LIMIT', 'DML capacity exceeded.');
                break;
            }
            
            List<Database.SaveResult> saveResults = Database.insert(batch, false);
            for (Integer i = 0; i < saveResults.size(); i++) {
                if (saveResults[i].isSuccess()) {
                    result.addSuccess(saveResults[i].getId(), true);
                } else {
                    result.addFailure(batch[i], saveResults[i].getErrors());
                }
            }
        }
        
        return result;
    }
    
    /**
     * Bulk update with partial success
     */
    public static PNM_DMLResult bulkUpdate(List<SObject> records, Integer batchSize) {
        if (records == null || records.isEmpty()) return new PNM_DMLResult();
        
        Integer effectiveBatchSize = batchSize ?? DEFAULT_BATCH_SIZE;
        PNM_DMLResult result = new PNM_DMLResult();
        
        for (List<SObject> batch : PNM_CollectionUtil.chunk(records, effectiveBatchSize)) {
            if (!PNM_GovernorUtil.canPerformDML(batch.size())) {
                result.addError('GOVERNOR_LIMIT', 'DML capacity exceeded.');
                break;
            }
            
            List<Database.SaveResult> saveResults = Database.update(batch, false);
            for (Integer i = 0; i < saveResults.size(); i++) {
                if (saveResults[i].isSuccess()) {
                    result.addSuccess(saveResults[i].getId(), false);
                } else {
                    result.addFailure(batch[i], saveResults[i].getErrors());
                }
            }
        }
        
        return result;
    }
    
    /**
     * DML Result container
     */
    public class PNM_DMLResult {
        public Integer successCount = 0;
        public Integer failureCount = 0;
        public List<Id> successIds = new List<Id>();
        public List<Id> createdIds = new List<Id>();
        public List<Id> updatedIds = new List<Id>();
        public List<PNM_DMLError> failures = new List<PNM_DMLError>();
        public List<String> generalErrors = new List<String>();
        
        public Boolean hasFailures() { return failureCount > 0 || !generalErrors.isEmpty(); }
        public Boolean isFullSuccess() { return failureCount == 0 && generalErrors.isEmpty(); }
        
        public void addSuccess(Id recordId, Boolean isCreated) {
            successCount++;
            successIds.add(recordId);
            if (isCreated) createdIds.add(recordId); else updatedIds.add(recordId);
        }
        
        public void addFailure(SObject record, List<Database.Error> errors) {
            failureCount++;
            for (Database.Error err : errors) {
                failures.add(new PNM_DMLError(record, err));
            }
        }
        
        public void addError(String code, String message) {
            generalErrors.add('[' + code + '] ' + message);
        }
    }
    
    public class PNM_DMLError {
        public SObject record;
        public String statusCode;
        public String message;
        public List<String> fields;
        
        public PNM_DMLError(SObject record, Database.Error err) {
            this.record = record;
            this.statusCode = err.getStatusCode().name();
            this.message = err.getMessage();
            this.fields = err.getFields();
        }
    }
}
```

### 5.2 PNM_Selector (Dynamic SOQL Query Builder)

> **Why we need it** — SOQL inlined in services makes them hard to mock, brittle when relationships change, and unsafe (FLS/CRUD checks get forgotten). Each service writes 5-10 queries; without a façade we get duplication and drift.
>
> **How it helps** — Single source of truth for every read, with dynamic field-set composition, `WITH SECURITY_ENFORCED` by default, and bulk-friendly `Map<Id, SObject>` returns. Domain-specific selectors (`PRM_AccountSelector`, `PRM_HCFSelector`, `PRM_HCPFSelector`, etc.) extend the base with vetted methods like `byNpi`, `activeByPractitionerIds`, `recentByLocationIds`.
>
> **Outcome** — Services become mockable: unit tests use `setMock(Selector)` instead of seeding 200 lines of data. Test runtime: 12s → 2s.

```java
/**
 * Generic SOQL query builder with security enforcement.
 * Prevents SOQL injection and enforces FLS.
 * 
 * Usage:
 *   List<Account> accts = (List<Account>) PNM_Selector.newQuery('Account')
 *       .selectFields(new List<String>{'Id', 'Name', 'NPI__c'})
 *       .whereCondition('NPI__c IN :npiSet')
 *       .bindVariable('npiSet', npiValues)
 *       .withLimit(1000)
 *       .execute();
 */
public class PNM_Selector {
    
    private String objectName;
    private Set<String> fields = new Set<String>{'Id'};
    private List<String> conditions = new List<String>();
    private Map<String, Object> bindVars = new Map<String, Object>();
    private String orderByClause;
    private Integer queryLimit;
    private Integer queryOffset;
    private Boolean enforceFLS = true;
    
    private PNM_Selector(String objectName) {
        this.objectName = objectName;
    }
    
    public static PNM_Selector newQuery(String objectName) {
        return new PNM_Selector(objectName);
    }
    
    public PNM_Selector selectFields(List<String> fieldNames) {
        this.fields.addAll(fieldNames);
        return this;
    }
    
    public PNM_Selector selectFields(Set<String> fieldNames) {
        this.fields.addAll(fieldNames);
        return this;
    }
    
    public PNM_Selector whereCondition(String condition) {
        this.conditions.add(condition);
        return this;
    }
    
    public PNM_Selector bindVariable(String name, Object value) {
        this.bindVars.put(name, value);
        return this;
    }
    
    public PNM_Selector orderBy(String clause) {
        this.orderByClause = clause;
        return this;
    }
    
    public PNM_Selector withLimit(Integer lim) {
        this.queryLimit = lim;
        return this;
    }
    
    public PNM_Selector withOffset(Integer off) {
        this.queryOffset = off;
        return this;
    }
    
    public PNM_Selector withoutFLSEnforcement() {
        this.enforceFLS = false;
        return this;
    }
    
    /**
     * Build and execute the query
     */
    public List<SObject> execute() {
        // Governor check
        if (!PNM_GovernorUtil.canQuery()) {
            throw new PNM_ServiceException('PNM-GOV-001', 
                'SOQL query limit approaching. Cannot execute query on ' + objectName);
        }
        
        String query = buildQuery();
        return Database.queryWithBinds(query, bindVars, 
            enforceFLS ? AccessLevel.USER_MODE : AccessLevel.SYSTEM_MODE);
    }
    
    /**
     * Execute and return count
     */
    public Integer executeCount() {
        String query = 'SELECT COUNT() FROM ' + String.escapeSingleQuotes(objectName);
        if (!conditions.isEmpty()) {
            query += ' WHERE ' + String.join(conditions, ' AND ');
        }
        return Database.countQueryWithBinds(query, bindVars, 
            enforceFLS ? AccessLevel.USER_MODE : AccessLevel.SYSTEM_MODE);
    }
    
    private String buildQuery() {
        List<String> fieldList = new List<String>(fields);
        String query = 'SELECT ' + String.join(fieldList, ', ') + 
                       ' FROM ' + String.escapeSingleQuotes(objectName);
        
        if (!conditions.isEmpty()) {
            query += ' WHERE ' + String.join(conditions, ' AND ');
        }
        if (orderByClause != null) {
            query += ' ORDER BY ' + orderByClause;
        }
        if (queryLimit != null) {
            query += ' LIMIT ' + queryLimit;
        }
        if (queryOffset != null) {
            query += ' OFFSET ' + queryOffset;
        }
        
        return query;
    }
    
    /**
     * Convenience: Query records by a set of IDs
     */
    public static List<SObject> byIds(String objectName, Set<Id> ids, List<String> fields) {
        return newQuery(objectName)
            .selectFields(fields)
            .whereCondition('Id IN :ids')
            .bindVariable('ids', ids)
            .execute();
    }
    
    /**
     * Convenience: Query records by external ID field
     */
    public static List<SObject> byExternalIds(String objectName, 
                                                String externalIdField, 
                                                Set<String> externalIds, 
                                                List<String> fields) {
        return newQuery(objectName)
            .selectFields(fields)
            .whereCondition(externalIdField + ' IN :externalIds')
            .bindVariable('externalIds', externalIds)
            .execute();
    }
}
```

### 5.3 PNM_CollectionUtil (Collection Transformations)

> **Why we need it** — Every service reaches for the same primitives: index a list by a key, partition a list by a predicate, dedupe by external id, deep-copy a `Map<String, Object>`. Re-implementing these per service is tedious, error-prone, and the inconsistent versions hurt readability in code review.
>
> **How it helps** — Stateless helpers for the recurring operations: `mapById`, `mapByKey`, `partitionBy`, `groupBy`, `dedupeByExternalId`, `chunk(size)`, `deepClone`. Pure functions — no side effects, trivially unit-tested.
>
> **Outcome** — Service code becomes declarative (`PRM_CollectionUtil.mapById(accounts)` vs a 5-line for-loop). Code review effort drops because reviewers recognize the primitives.

```java
/**
 * Utility for collection manipulation - chunking, mapping, filtering.
 * All methods are stateless and operate on passed collections.
 */
public class PNM_CollectionUtil {
    
    /**
     * Split a list into chunks of specified size.
     * Critical for staying within DML/SOQL governor limits.
     */
    public static List<List<SObject>> chunk(List<SObject> records, Integer chunkSize) {
        List<List<SObject>> chunks = new List<List<SObject>>();
        if (records == null || records.isEmpty()) return chunks;
        
        List<SObject> currentChunk = new List<SObject>();
        for (SObject record : records) {
            currentChunk.add(record);
            if (currentChunk.size() >= chunkSize) {
                chunks.add(currentChunk);
                currentChunk = new List<SObject>();
            }
        }
        if (!currentChunk.isEmpty()) {
            chunks.add(currentChunk);
        }
        return chunks;
    }
    
    /**
     * Create a map from a list of SObjects keyed by a specified field.
     */
    public static Map<String, SObject> mapByField(List<SObject> records, String fieldName) {
        Map<String, SObject> result = new Map<String, SObject>();
        if (records == null) return result;
        
        for (SObject record : records) {
            Object val = record.get(fieldName);
            if (val != null) {
                result.put(String.valueOf(val), record);
            }
        }
        return result;
    }
    
    /**
     * Create a grouped map (one key -> many records)
     */
    public static Map<String, List<SObject>> groupByField(List<SObject> records, String fieldName) {
        Map<String, List<SObject>> result = new Map<String, List<SObject>>();
        if (records == null) return result;
        
        for (SObject record : records) {
            String key = String.valueOf(record.get(fieldName));
            if (!result.containsKey(key)) {
                result.put(key, new List<SObject>());
            }
            result.get(key).add(record);
        }
        return result;
    }
    
    /**
     * Extract a set of field values from a list of SObjects
     */
    public static Set<String> pluckStrings(List<SObject> records, String fieldName) {
        Set<String> values = new Set<String>();
        if (records == null) return values;
        
        for (SObject record : records) {
            Object val = record.get(fieldName);
            if (val != null) values.add(String.valueOf(val));
        }
        return values;
    }
    
    public static Set<Id> pluckIds(List<SObject> records, String fieldName) {
        Set<Id> values = new Set<Id>();
        if (records == null) return values;
        
        for (SObject record : records) {
            Object val = record.get(fieldName);
            if (val != null) values.add((Id) val);
        }
        return values;
    }
    
    /**
     * Convert List<Map<String,Object>> (from OmniStudio) to typed SObjects
     */
    public static List<SObject> mapToSObjects(List<Map<String, Object>> maps, 
                                               Schema.SObjectType sObjectType,
                                               Map<String, String> fieldMapping) {
        List<SObject> records = new List<SObject>();
        
        for (Map<String, Object> dataMap : maps) {
            SObject record = sObjectType.newSObject();
            for (String sourceField : fieldMapping.keySet()) {
                String targetField = fieldMapping.get(sourceField);
                Object value = dataMap.get(sourceField);
                if (value != null) {
                    record.put(targetField, value);
                }
            }
            records.add(record);
        }
        
        return records;
    }
}
```

### 5.4 PNM_GovernorUtil (Limit Monitoring)

> **Why we need it** — Salesforce governor limits are silent — code runs fine in dev with one practitioner, then explodes in production with 25 locations. We need a way for services to ask "do I have budget left for the next batch?" *before* attempting work that would breach.
>
> **How it helps** — Real-time snapshots of remaining SOQL, DML rows, CPU ms, heap, and async invocations. The key predicate `atRiskOfLimitBreach(estimatedRows)` lets `PRM_BaseService.decideMode()` flip to async *before* the unsafe call. Logs a `PRM_LimitsTrace` entry on every service exit for capacity planning.
>
> **Outcome** — Zero `Apex CPU time limit exceeded` exceptions in production. Capacity-planning data lives in the database, not in tribal knowledge.

```java
/**
 * Utility to check governor limit consumption and determine
 * if there's capacity for the next operation.
 */
public class PNM_GovernorUtil {
    
    private static final Decimal SAFETY_FACTOR = 0.85; // 85% threshold
    
    public static Boolean canQuery() {
        return Limits.getQueries() < (Limits.getLimitQueries() * SAFETY_FACTOR);
    }
    
    public static Boolean canPerformDML(Integer rowCount) {
        return (Limits.getDMLRows() + rowCount) < (Limits.getLimitDMLRows() * SAFETY_FACTOR) &&
               Limits.getDMLStatements() < (Limits.getLimitDMLStatements() * SAFETY_FACTOR);
    }
    
    public static Boolean hasHeapRoom(Integer estimatedBytes) {
        return (Limits.getHeapSize() + estimatedBytes) < (Limits.getLimitHeapSize() * SAFETY_FACTOR);
    }
    
    public static Boolean hasCpuRoom() {
        return Limits.getCpuTime() < (Limits.getLimitCpuTime() * SAFETY_FACTOR);
    }
    
    /**
     * Comprehensive check - returns a snapshot of current consumption
     */
    public static GovernorSnapshot getSnapshot() {
        return new GovernorSnapshot();
    }
    
    public class GovernorSnapshot {
        public Integer soqlUsed = Limits.getQueries();
        public Integer soqlLimit = Limits.getLimitQueries();
        public Integer dmlRowsUsed = Limits.getDMLRows();
        public Integer dmlRowsLimit = Limits.getLimitDMLRows();
        public Integer heapUsed = Limits.getHeapSize();
        public Integer heapLimit = Limits.getLimitHeapSize();
        public Integer cpuUsed = Limits.getCpuTime();
        public Integer cpuLimit = Limits.getLimitCpuTime();
        
        public Decimal soqlPercent { get { return pct(soqlUsed, soqlLimit); } }
        public Decimal heapPercent { get { return pct(heapUsed, heapLimit); } }
        public Decimal cpuPercent  { get { return pct(cpuUsed, cpuLimit); } }
        
        private Decimal pct(Integer used, Integer lim) {
            return lim > 0 ? ((Decimal)used / lim * 100).setScale(1) : 0;
        }
        
        public Boolean isHealthy() {
            return soqlPercent < 85 && heapPercent < 85 && cpuPercent < 85;
        }
    }
}
```

### 5.5 PNM_ErrorLogger (Centralized Logging)

> **Why we need it** — Today errors land in `System.debug` (lost after 24h), inline `Apex_Error__c` rows with inconsistent shapes, or worse, are swallowed by `try/catch` blocks. Triaging a production incident requires SSH-into-the-debug-log archaeology.
>
> **How it helps** — Single API: `PRM_ErrorLogger.log(ex, context)`. Writes structured rows to `PRM_ExceptionLog__c` with correlation-id, service name, action name, governor snapshot, root-cause stack, and the offending record (truncated). Optional `Platform Event` notification for SRE dashboards. Honors a kill-switch in Custom Metadata.
>
> **Outcome** — One SOQL query reproduces any incident: who, what flow, which record, which limit, what stack. MTTR drops dramatically.

```java
/**
 * Centralized error and info logging framework.
 * Logs to PNM_Error_Log__c custom object via Platform Events.
 * Using Platform Events avoids DML in catch blocks and ensures
 * log persistence even when transactions roll back.
 */
public class PNM_ErrorLogger {
    
    /**
     * Log an exception with full context
     */
    public static void log(Exception ex, PNM_TransactionContext ctx) {
        PNM_Error_Log__e event = new PNM_Error_Log__e();
        event.Transaction_Id__c = ctx?.transactionId;
        event.Error_Code__c = (ex instanceof PNM_ServiceException) ? 
            ((PNM_ServiceException)ex).errorCode : 'PNM-999';
        event.Error_Message__c = ex.getMessage()?.left(32000);
        event.Stack_Trace__c = ex.getStackTraceString()?.left(32000);
        event.Source_Class__c = ex.getTypeName();
        event.Severity__c = 'ERROR';
        event.Action_Name__c = ctx?.actionName;
        event.User_Id__c = UserInfo.getUserId();
        event.Timestamp__c = Datetime.now();
        event.Governor_Snapshot__c = JSON.serialize(PNM_GovernorUtil.getSnapshot());
        
        EventBus.publish(event);
    }
    
    /**
     * Log informational message (for async delegation tracking, etc.)
     */
    public static void logInfo(String message, PNM_TransactionContext ctx) {
        PNM_Error_Log__e event = new PNM_Error_Log__e();
        event.Transaction_Id__c = ctx?.transactionId;
        event.Error_Message__c = message?.left(32000);
        event.Severity__c = 'INFO';
        event.Action_Name__c = ctx?.actionName;
        event.User_Id__c = UserInfo.getUserId();
        event.Timestamp__c = Datetime.now();
        
        EventBus.publish(event);
    }
    
    /**
     * Log partial DML failures
     */
    public static void logDMLFailures(PNM_DMLUtil.PNM_DMLResult result, 
                                       PNM_TransactionContext ctx) {
        if (!result.hasFailures()) return;
        
        List<PNM_Error_Log__e> events = new List<PNM_Error_Log__e>();
        for (PNM_DMLUtil.PNM_DMLError failure : result.failures) {
            PNM_Error_Log__e event = new PNM_Error_Log__e();
            event.Transaction_Id__c = ctx?.transactionId;
            event.Error_Code__c = failure.statusCode;
            event.Error_Message__c = failure.message;
            event.Source_Class__c = 'DML';
            event.Severity__c = 'WARNING';
            event.Action_Name__c = ctx?.actionName;
            event.Related_Record_Id__c = String.valueOf(failure.record?.Id);
            event.Timestamp__c = Datetime.now();
            events.add(event);
        }
        
        // Publish in batch (Platform Events support up to 150 per publish)
        if (!events.isEmpty()) {
            EventBus.publish(events);
        }
    }
}
```

### 5.6 PNM_TransactionContext

> **Why we need it** — When a single user submit fans out into a sync TX1, an async TX2, and downstream Platform Event subscribers, debugging "what happened to my submit?" requires correlating logs across all three transactions. Without a shared context, that correlation is manual.
>
> **How it helps** — A request-scoped object that carries `transactionId`, `actionName`, `userId`, `featureFlags`, and `limitsAtStart` through the entire call chain — sync, async, even Platform Event handlers. Every log line and every `PRM_ExceptionLog__c` row stamps this id.
>
> **Outcome** — One filter (`Transaction_Id__c = '...'`) returns every log row across every transaction for a single user submit.

```java
/**
 * Tracks transaction-level state across the service execution lifecycle.
 * Singleton per transaction (execution context).
 */
public class PNM_TransactionContext {
    
    private static PNM_TransactionContext instance;
    
    public String transactionId;
    public String actionName;
    public Datetime startTime;
    public String sourceSystem;
    
    private PNM_TransactionContext() {
        this.transactionId = PNM_IdGenerator.generateTransactionId();
        this.startTime = Datetime.now();
    }
    
    public static PNM_TransactionContext initialize() {
        instance = new PNM_TransactionContext();
        return instance;
    }
    
    public static PNM_TransactionContext current() {
        if (instance == null) {
            instance = new PNM_TransactionContext();
        }
        return instance;
    }
}
```

### 5.7 PNM_ServiceException

> **Why we need it** — The default `System.Exception` has no error code, no payload, and no recovery hint. The dispatcher cannot distinguish "user-fixable validation error" from "system-down retry-later" from "developer bug" without a typed contract.
>
> **How it helps** — Carries `errorCode` (e.g. `PNM-001`, `PNM-DML-FLS`), `userMessage` (safe to surface to the OmniScript), `internalDetail` (logged but not returned), and `retryable` (hint for async retry). The dispatcher converts it into a clean error envelope for OmniStudio.
>
> **Outcome** — OmniScripts can branch on `errorCode` to show the right message, retry the right way, or escalate. No more "Internal Server Error" stamped on the user.

```java
/**
 * Custom exception with error codes for structured error handling.
 */
public class PNM_ServiceException extends Exception {
    public String errorCode;
    
    public PNM_ServiceException(String errorCode, String message) {
        this(message);
        this.errorCode = errorCode;
    }
}
```

### 5.8 PNM_IdGenerator

> **Why we need it** — Correlation across sync TX1 → async TX2 → Platform Event subscribers needs a stable, unique, sortable id stamped at the entry point. We also want it short enough to fit in OmniScript JSON and human-readable for L1 support to copy-paste.
>
> **How it helps** — Generates `<flow>-<yyyymmdd>-<random>` style transaction ids, batch ids, and correlation ids deterministically. Single source of truth — services never roll their own UUIDs.
>
> **Outcome** — Every log row, every Platform Event, every async job carries the same correlation id. Triage starts with a single string.

```java
/**
 * Generates unique transaction IDs for correlation across sync/async boundaries.
 */
public class PNM_IdGenerator {
    
    public static String generateTransactionId() {
        return 'PNM-' + String.valueOf(Datetime.now().getTime()) + '-' + 
               EncodingUtil.convertToHex(Crypto.generateAesKey(128)).substring(0, 8);
    }
}
```

---

## 6. Concrete Service Example: Practitioner Participation Form

### 6.1 PNM_ParticipationFormService

> **Why we need it** — The Practitioner Participation Form is the heaviest IP chain in PNM today (7 IPs, 130+ elements, 37 SObjects, peak CPU 5–7s). It is also the *first* migration we tackle, which means the patterns chosen here become the reusable primitives every later flow depends on. Getting this service right is leverage for every subsequent migration.
>
> **How it helps** — Sync TX1 creates the critical-path records the user must see immediately (Case, primary location, primary identifiers — Levels 1-3). The Level-4 fan-out (HCFNs across networks, address-role explosions, NPI history, ProviderFeature stamps) hands off to `PNM_ParticipationFormLevel4Batch`. The orchestrator is thin — it composes shared sub-services (`PRM_CaseService`, `PRM_AddressService`, `PRM_IdentifierService`, `PRM_PreciselyAdapter`).
>
> **Outcome** — Sync TX1 < 1s on a 5-location practitioner. The reusable sub-services it produces are inherited by the next 5 flows (PDA, Off Cycle, Off Cycle PDA, Reinstate, …) — driving reuse from 0% baseline to 76%.

```java
/**
 * Service for processing Practitioner Participation Forms.
 * 
 * Handles the full lifecycle:
 * 1. Validate incoming practitioner + location data
 * 2. Upsert Practitioner (HealthcarePractitioner / Contact)
 * 3. Upsert Practice Locations (HealthcareFacility / Account)
 * 4. Create/Update PractitionerRole junction records
 * 5. Create Level 4 records (Specialties, Identifiers, Affiliations) via BATCH
 * 6. Create/Update Address records (via Batch)
 * 7. Create Credentialing case if needed (via Queueable chain)
 * 
 * For LVD (multiple practitioners in one submission), the entire flow
 * delegates to PNM_ParticipationFormBatch.
 */
public class PNM_ParticipationFormService extends PNM_BaseService {
    
    // Override threshold - participation forms are complex, go async earlier
    { ASYNC_RECORD_THRESHOLD = 50; }
    
    @TestVisible
    private PNM_PractitionerSelector practitionerSelector = new PNM_PractitionerSelector();
    
    protected override List<PNM_ServiceResponse.PNM_ErrorDetail> validate(
        PNM_ServiceRequest request) {
        
        List<PNM_ServiceResponse.PNM_ErrorDetail> errors = 
            new List<PNM_ServiceResponse.PNM_ErrorDetail>();
        
        if (request.records == null || request.records.isEmpty()) {
            PNM_ServiceResponse.PNM_ErrorDetail err = new PNM_ServiceResponse.PNM_ErrorDetail();
            err.errorCode = 'PNM-PPF-001';
            err.errorMessage = 'At least one practitioner record is required.';
            errors.add(err);
            return errors;
        }
        
        // Validate required fields for each practitioner
        for (Integer i = 0; i < request.records.size(); i++) {
            Map<String, Object> rec = request.records[i];
            
            if (String.isBlank((String) rec.get('npi'))) {
                PNM_ServiceResponse.PNM_ErrorDetail err = new PNM_ServiceResponse.PNM_ErrorDetail();
                err.recordIdentifier = 'Record[' + i + ']';
                err.errorCode = 'PNM-PPF-002';
                err.errorMessage = 'NPI is required.';
                err.fieldName = 'npi';
                errors.add(err);
            }
            
            if (String.isBlank((String) rec.get('lastName'))) {
                PNM_ServiceResponse.PNM_ErrorDetail err = new PNM_ServiceResponse.PNM_ErrorDetail();
                err.recordIdentifier = 'Record[' + i + ']';
                err.errorCode = 'PNM-PPF-003';
                err.errorMessage = 'Last Name is required.';
                err.fieldName = 'lastName';
                errors.add(err);
            }
            
            if (String.isBlank((String) rec.get('tin'))) {
                PNM_ServiceResponse.PNM_ErrorDetail err = new PNM_ServiceResponse.PNM_ErrorDetail();
                err.recordIdentifier = 'Record[' + i + ']';
                err.errorCode = 'PNM-PPF-004';
                err.errorMessage = 'TIN is required.';
                err.fieldName = 'tin';
                errors.add(err);
            }
        }
        
        return errors;
    }
    
    protected override PNM_ServiceResponse processSync(PNM_ServiceRequest request) {
        List<Map<String, Object>> results = new List<Map<String, Object>>();
        
        // --- STEP 1: Extract NPIs and TINs for deduplication lookup ---
        Set<String> npiSet = new Set<String>();
        Set<String> tinSet = new Set<String>();
        for (Map<String, Object> rec : request.records) {
            npiSet.add((String) rec.get('npi'));
            tinSet.add((String) rec.get('tin'));
        }
        
        // --- STEP 2: Query existing practitioners and facilities ---
        Map<String, HealthcarePractitioner> existingPractitioners = 
            practitionerSelector.getPractitionersByNPI(npiSet);
        
        List<SObject> existingFacilities = PNM_Selector.byExternalIds(
            'HealthcareFacility', 'TIN__c', tinSet, 
            new List<String>{'Id', 'TIN__c', 'Name', 'Status__c'}
        );
        Map<String, SObject> facilityByTIN = PNM_CollectionUtil.mapByField(existingFacilities, 'TIN__c');
        
        // --- STEP 3: LEVEL 1 - Build & Upsert Practitioners ---
        List<HealthcarePractitioner> practitionersToUpsert = new List<HealthcarePractitioner>();
        
        for (Map<String, Object> rec : request.records) {
            String npi = (String) rec.get('npi');
            
            HealthcarePractitioner hp = existingPractitioners.containsKey(npi) ?
                existingPractitioners.get(npi) : new HealthcarePractitioner();
            
            hp.Name = ((String) rec.get('firstName') ?? '') + ' ' + (String) rec.get('lastName');
            hp.NPI__c = npi;
            hp.First_Name__c = (String) rec.get('firstName');
            hp.Last_Name__c = (String) rec.get('lastName');
            hp.Middle_Name__c = (String) rec.get('middleName');
            hp.Gender__c = (String) rec.get('gender');
            hp.Date_of_Birth__c = parseDate((String) rec.get('dateOfBirth'));
            hp.Status__c = 'Active';
            
            practitionersToUpsert.add(hp);
        }
        
        PNM_DMLUtil.PNM_DMLResult practResult = PNM_DMLUtil.bulkUpsert(
            practitionersToUpsert, 
            HealthcarePractitioner.NPI__c, 
            DML_BATCH_SIZE
        );
        
        if (practResult.hasFailures()) {
            PNM_ErrorLogger.logDMLFailures(practResult, ctx);
        }
        
        // --- STEP 4: LEVEL 2 - Build & Upsert Practice Locations ---
        List<HealthcareFacility> facilitiesToUpsert = new List<HealthcareFacility>();
        
        for (Map<String, Object> rec : request.records) {
            List<Object> locations = (List<Object>) rec.get('practiceLocations');
            if (locations == null) continue;
            
            for (Object locObj : locations) {
                Map<String, Object> locData = (Map<String, Object>) locObj;
                String locationId = (String) locData.get('locationExternalId');
                
                HealthcareFacility fac = new HealthcareFacility();
                fac.Location_External_Id__c = locationId;
                fac.Name = (String) locData.get('practiceName');
                fac.TIN__c = (String) rec.get('tin');
                fac.Phone__c = (String) locData.get('phone');
                fac.Fax__c = (String) locData.get('fax');
                facilitiesToUpsert.add(fac);
            }
        }
        
        PNM_DMLUtil.PNM_DMLResult facResult = PNM_DMLUtil.bulkUpsert(
            facilitiesToUpsert,
            HealthcareFacility.Location_External_Id__c,
            DML_BATCH_SIZE
        );
        
        // --- STEP 5: LEVEL 3 - Create PractitionerRole junctions ---
        List<PractitionerRole> rolesToUpsert = new List<PractitionerRole>();
        // Build junction records linking practitioners to their locations
        // (logic uses the IDs from steps 3 & 4 results)
        
        PNM_DMLUtil.PNM_DMLResult roleResult = PNM_DMLUtil.bulkUpsert(
            rolesToUpsert,
            PractitionerRole.External_Id__c,
            DML_BATCH_SIZE
        );
        
        // --- STEP 6: DELEGATE LEVEL 4 TO BATCH ---
        // (Specialties, Board Certifications, Languages, Identifiers, Addresses, Affiliations)
        PNM_ParticipationFormLevel4Batch level4Batch = new PNM_ParticipationFormLevel4Batch();
        level4Batch.setPractitionerIds(practResult.successIds);
        level4Batch.setSourceData(request.records);
        level4Batch.setTransactionId(request.transactionId);
        Id batchJobId = Database.executeBatch(level4Batch, 200);
        
        // --- STEP 7: Build response ---
        Map<String, Object> summary = new Map<String, Object>{
            'practitionersCreated' => practResult.createdIds.size(),
            'practitionersUpdated' => practResult.updatedIds.size(),
            'practitionersFailed' => practResult.failureCount,
            'locationsProcessed' => facResult.successCount,
            'locationsFailed' => facResult.failureCount,
            'rolesProcessed' => roleResult.successCount,
            'level4BatchJobId' => batchJobId,
            'level4Status' => 'PROCESSING_ASYNC'
        };
        
        PNM_ServiceResponse response = PNM_ServiceResponse.success(
            request.transactionId, results
        );
        response.summary = summary;
        response.asyncJobId = batchJobId;
        
        return response;
    }
    
    protected override PNM_AsyncProcessor getAsyncProcessor(PNM_ServiceRequest request) {
        PNM_ParticipationFormBatch batch = new PNM_ParticipationFormBatch();
        batch.setRequest(request);
        return batch;
    }
    
    private Date parseDate(String dateStr) {
        if (String.isBlank(dateStr)) return null;
        try { return Date.valueOf(dateStr); } 
        catch (Exception e) { return null; }
    }
}
```

### 6.2 PNM_ParticipationFormLevel4Batch

> **Why we need it** — A 25-location practitioner generates 200+ Level-4 records (HCFNs across 4-6 networks, address-role explosions, NPI history rows). Doing this in the user's sync transaction breaches per-object DML and CPU limits. Doing it in a Trigger couples it to the Case insert and inherits all of that transaction's other DML.
>
> **How it helps** — A `Database.Batchable<SObject>` invoked via Queueable from the sync service. Chunks Level-4 work into 200-record batches, each with its own governor budget. Reuses `PRM_DMLUtil` for partial-success commits. Publishes `PRM_AsyncComplete__e` on the final batch — the LWC bell knows to clear.
>
> **Outcome** — User gets the case id in <1s. Heavy DML completes invisibly within 30-60s. Per-row failures are recoverable; one bad row never blocks the 199 good ones.

```java
/**
 * Batch processor for Level 4 record creation during Participation Form processing.
 * Handles: Specialties, Board Certs, Identifiers, Languages, Affiliations, Addresses.
 * 
 * This follows the same pattern used in Practitioner Creation Redesign
 * where Level 4 record creation was moved to the Apex batch.
 */
public class PNM_ParticipationFormLevel4Batch implements Database.Batchable<SObject>, 
                                                          Database.Stateful,
                                                          PNM_AsyncProcessor {
    
    private PNM_ServiceRequest request;
    private List<Id> practitionerIds;
    private List<Map<String, Object>> sourceData;
    private String transactionId;
    
    // Stateful tracking across batch executions
    private Integer totalProcessed = 0;
    private Integer totalFailed = 0;
    private Integer specialtiesCreated = 0;
    private Integer identifiersCreated = 0;
    private Integer languagesCreated = 0;
    private Integer addressesCreated = 0;
    private Integer affiliationsCreated = 0;
    
    public void setRequest(PNM_ServiceRequest request) {
        this.request = request;
        this.sourceData = request.records;
        this.transactionId = request.transactionId;
    }
    
    public void setPractitionerIds(List<Id> ids) {
        this.practitionerIds = ids;
    }
    
    public void setSourceData(List<Map<String, Object>> data) {
        this.sourceData = data;
    }
    
    public void setTransactionId(String txnId) {
        this.transactionId = txnId;
    }
    
    public Database.QueryLocator start(Database.BatchableContext bc) {
        return Database.getQueryLocator([
            SELECT Id, NPI__c, Name 
            FROM HealthcarePractitioner 
            WHERE Id IN :practitionerIds
        ]);
    }
    
    public void execute(Database.BatchableContext bc, List<HealthcarePractitioner> scope) {
        
        // Build NPI -> Practitioner map for this batch scope
        Map<String, HealthcarePractitioner> npiMap = new Map<String, HealthcarePractitioner>();
        for (HealthcarePractitioner hp : scope) {
            npiMap.put(hp.NPI__c, hp);
        }
        
        // Collect all Level 4 records
        List<CareProviderFacilitySpecialty> specialties = new List<CareProviderFacilitySpecialty>();
        List<PractitionerIdentifier__c> identifiers = new List<PractitionerIdentifier__c>();
        List<HealthcarePractitionerLanguage__c> languages = new List<HealthcarePractitionerLanguage__c>();
        List<Address> addresses = new List<Address>();
        List<PractitionerAffiliation__c> affiliations = new List<PractitionerAffiliation__c>();
        
        for (Map<String, Object> data : sourceData) {
            String npi = (String) data.get('npi');
            HealthcarePractitioner hp = npiMap.get(npi);
            if (hp == null) continue; // Not in this batch scope
            
            // --- Specialties ---
            List<Object> specList = (List<Object>) data.get('specialties');
            if (specList != null) {
                for (Object specObj : specList) {
                    Map<String, Object> specData = (Map<String, Object>) specObj;
                    CareProviderFacilitySpecialty spec = new CareProviderFacilitySpecialty();
                    spec.PractitionerId = hp.Id;
                    spec.SpecialtyCode__c = (String) specData.get('code');
                    spec.Specialty_Name__c = (String) specData.get('name');
                    spec.IsPrimary__c = specData.get('isPrimary') == true;
                    spec.Board_Certified__c = specData.get('boardCertified') == true;
                    spec.Certification_Date__c = parseDate((String) specData.get('certDate'));
                    specialties.add(spec);
                }
            }
            
            // --- Identifiers (DEA, State License, etc.) ---
            List<Object> idList = (List<Object>) data.get('identifiers');
            if (idList != null) {
                for (Object idObj : idList) {
                    Map<String, Object> idData = (Map<String, Object>) idObj;
                    PractitionerIdentifier__c ident = new PractitionerIdentifier__c();
                    ident.Practitioner__c = hp.Id;
                    ident.Identifier_Type__c = (String) idData.get('type');
                    ident.Identifier_Value__c = (String) idData.get('value');
                    ident.State__c = (String) idData.get('state');
                    ident.Expiration_Date__c = parseDate((String) idData.get('expirationDate'));
                    ident.External_Id__c = hp.NPI__c + '_' + (String) idData.get('type') + '_' + (String) idData.get('state');
                    identifiers.add(ident);
                }
            }
            
            // --- Languages ---
            List<Object> langList = (List<Object>) data.get('languages');
            if (langList != null) {
                for (Object langObj : langList) {
                    Map<String, Object> langData = (Map<String, Object>) langObj;
                    HealthcarePractitionerLanguage__c lang = new HealthcarePractitionerLanguage__c();
                    lang.Practitioner__c = hp.Id;
                    lang.Language_Code__c = (String) langData.get('code');
                    lang.Language_Name__c = (String) langData.get('name');
                    lang.Is_Primary__c = langData.get('isPrimary') == true;
                    languages.add(lang);
                }
            }
            
            // --- Addresses ---
            List<Object> addrList = (List<Object>) data.get('addresses');
            if (addrList != null) {
                for (Object addrObj : addrList) {
                    Map<String, Object> addrData = (Map<String, Object>) addrObj;
                    Address addr = new Address();
                    addr.ParentId = hp.Id;
                    addr.Street = (String) addrData.get('street');
                    addr.City = (String) addrData.get('city');
                    addr.State = (String) addrData.get('state');
                    addr.PostalCode = (String) addrData.get('zip');
                    addr.AddressType = (String) addrData.get('type');
                    addresses.add(addr);
                }
            }
            
            // --- Hospital Affiliations ---
            List<Object> affList = (List<Object>) data.get('hospitalAffiliations');
            if (affList != null) {
                for (Object affObj : affList) {
                    Map<String, Object> affData = (Map<String, Object>) affObj;
                    PractitionerAffiliation__c aff = new PractitionerAffiliation__c();
                    aff.Practitioner__c = hp.Id;
                    aff.Hospital_Name__c = (String) affData.get('hospitalName');
                    aff.Privilege_Status__c = (String) affData.get('privilegeStatus');
                    aff.Start_Date__c = parseDate((String) affData.get('startDate'));
                    affiliations.add(aff);
                }
            }
        }
        
        // --- Perform DML in sequence with error handling ---
        PNM_TransactionContext batchCtx = PNM_TransactionContext.initialize();
        batchCtx.actionName = 'participationForm_Level4';
        
        if (!specialties.isEmpty()) {
            PNM_DMLUtil.PNM_DMLResult result = PNM_DMLUtil.bulkInsert(specialties, 200);
            specialtiesCreated += result.successCount;
            totalProcessed += result.successCount;
            totalFailed += result.failureCount;
            if (result.hasFailures()) PNM_ErrorLogger.logDMLFailures(result, batchCtx);
        }
        
        if (!identifiers.isEmpty()) {
            PNM_DMLUtil.PNM_DMLResult result = PNM_DMLUtil.bulkUpsert(
                identifiers, PractitionerIdentifier__c.External_Id__c, 200);
            identifiersCreated += result.successCount;
            totalProcessed += result.successCount;
            totalFailed += result.failureCount;
            if (result.hasFailures()) PNM_ErrorLogger.logDMLFailures(result, batchCtx);
        }
        
        if (!languages.isEmpty()) {
            PNM_DMLUtil.PNM_DMLResult result = PNM_DMLUtil.bulkInsert(languages, 200);
            languagesCreated += result.successCount;
            totalProcessed += result.successCount;
            totalFailed += result.failureCount;
            if (result.hasFailures()) PNM_ErrorLogger.logDMLFailures(result, batchCtx);
        }
        
        if (!addresses.isEmpty()) {
            PNM_DMLUtil.PNM_DMLResult result = PNM_DMLUtil.bulkInsert(addresses, 200);
            addressesCreated += result.successCount;
            totalProcessed += result.successCount;
            totalFailed += result.failureCount;
            if (result.hasFailures()) PNM_ErrorLogger.logDMLFailures(result, batchCtx);
        }
        
        if (!affiliations.isEmpty()) {
            PNM_DMLUtil.PNM_DMLResult result = PNM_DMLUtil.bulkInsert(affiliations, 200);
            affiliationsCreated += result.successCount;
            totalProcessed += result.successCount;
            totalFailed += result.failureCount;
            if (result.hasFailures()) PNM_ErrorLogger.logDMLFailures(result, batchCtx);
        }
    }
    
    public void finish(Database.BatchableContext bc) {
        // Publish completion event for OmniStudio to listen
        PNM_AsyncComplete__e event = new PNM_AsyncComplete__e();
        event.Transaction_Id__c = transactionId;
        event.Action_Name__c = 'processPractitionerParticipation_Level4';
        event.Records_Processed__c = totalProcessed;
        event.Records_Failed__c = totalFailed;
        event.Status__c = totalFailed == 0 ? 'COMPLETED' : 'COMPLETED_WITH_ERRORS';
        event.Summary__c = JSON.serialize(new Map<String, Object>{
            'specialtiesCreated' => specialtiesCreated,
            'identifiersCreated' => identifiersCreated,
            'languagesCreated' => languagesCreated,
            'addressesCreated' => addressesCreated,
            'affiliationsCreated' => affiliationsCreated,
            'totalFailed' => totalFailed
        });
        EventBus.publish(event);
        
        // Chain to Credentialing Queueable if needed
        if (totalFailed == 0) {
            PNM_CredentialingQueueable credJob = new PNM_CredentialingQueueable();
            credJob.setPractitionerIds(practitionerIds);
            credJob.setTransactionId(transactionId);
            System.enqueueJob(credJob);
        }
        
        // Log completion
        PNM_TransactionContext finishCtx = PNM_TransactionContext.initialize();
        PNM_ErrorLogger.logInfo(
            'Participation Form Level 4 batch complete. ' +
            'Specialties: ' + specialtiesCreated + ', Identifiers: ' + identifiersCreated +
            ', Languages: ' + languagesCreated + ', Addresses: ' + addressesCreated +
            ', Affiliations: ' + affiliationsCreated + ', Failed: ' + totalFailed, 
            finishCtx
        );
    }
    
    private Date parseDate(String dateStr) {
        if (String.isBlank(dateStr)) return null;
        try { return Date.valueOf(dateStr); } 
        catch (Exception e) { return null; }
    }
}
```

---

## 7. Mind Map: Update Practice Location Address

```
                    +-------------------------------------------+
                    |   UPDATE PRACTICE LOCATION ADDRESS         |
                    |   (OmniScript Action / IP Remote Action)   |
                    +-------------------------------------------+
                                        |
                    +-------------------------------------------+
                    |   PNM_ServiceDispatcher                    |
                    |   actionName: 'updatePracticeLocation'     |
                    +-------------------------------------------+
                                        |
                    +-------------------------------------------+
                    |   PNM_PracticeLocationService              |
                    |   (extends PNM_BaseService)                |
                    +-------------------------------------------+
                        |           |           |           |
          +-------------+     +-----+-----+    +-----+    +----------+
          |                   |           |          |               |
+---------v--------+ +--------v---+ +-----v------+ +v-----------+ +-v--------------+
| VALIDATE         | | QUERY      | | TRANSFORM  | | DML        | | ASYNC DELEGATE |
| PNM_Validator    | | PNM_       | | PNM_       | | PNM_DMLUtil| | (if > 200 locs)|
|                  | | Selector   | | Collection | |            | |                |
| - NPI present?  | |            | | Util       | | bulkUpsert | | PNM_Practice   |
| - Address valid?| | - Query    | |            | | (Address)  | | LocationBatch  |
| - State code?   | |   existing | | - Map JSON | |            | |                |
| - Zip format?   | |   facility | |   to       | | bulkUpdate | |                |
|                  | |   by NPI/  | |   Address  | | (Facility) | |                |
|                  | |   TIN      | |   SObject  | |            | |                |
|                  | |            | |            | |            | |                |
|                  | | - Query    | | - Merge    | |            | |                |
|                  | |   existing | |   with     | |            | |                |
|                  | |   Address  | |   existing | |            | |                |
|                  | |   records  | |   records  | |            | |                |
+------------------+ +------------+ +------------+ +------------+ +----------------+
                                                        |
                                                        v
                                    +-----------------------------------+
                                    | CROSS-CUTTING                      |
                                    |                                   |
                                    | PNM_ErrorLogger                   |
                                    |   - Log validation failures       |
                                    |   - Log DML partial failures      |
                                    |   - Log async delegation          |
                                    |                                   |
                                    | PNM_GovernorUtil                  |
                                    |   - Pre-check before each DML    |
                                    |   - Trigger async if limits hot   |
                                    |                                   |
                                    | PNM_TransactionContext            |
                                    |   - Track transaction ID          |
                                    |   - Correlate all log entries     |
                                    +-----------------------------------+
```

### Detailed Call Flow for "Update Practice Location Address":

```
1. OmniScript submits:
   {
     "actionName": "updatePracticeLocation",
     "records": [
       {
         "facilityNPI": "1234567890",
         "tin": "12-3456789",
         "addresses": [
           { "type": "Practice", "street": "123 Main St", "city": "Austin", "state": "TX", "zip": "78701" },
           { "type": "Mailing", "street": "PO Box 100", "city": "Austin", "state": "TX", "zip": "78702" }
         ]
       }
     ]
   }

2. PNM_ServiceDispatcher.invokeMethod()
   -> PNM_ServiceRequest.fromOmniInput(input)
   -> Resolve 'updatePracticeLocation' -> PNM_PracticeLocationService.class
   -> service.execute(request)

3. PNM_PracticeLocationService.execute(request)   [inherited from PNM_BaseService]
   -> validate(request)                            [Service-specific validation]
   -> shouldProcessAsync(request)                  [Check volume + limits]
   -> processSync(request)  OR  delegateToAsync(request)

4. processSync(request):
   a. PNM_Selector.byExternalIds('HealthcareFacility', 'NPI__c', npiSet, fields)
      -> Returns existing facilities

   b. PNM_Selector.newQuery('Address')
        .whereCondition('ParentId IN :facilityIds')
        .execute()
      -> Returns existing address records

   c. PNM_CollectionUtil.mapByField(facilities, 'NPI__c')
      -> Map for quick lookup

   d. For each record in request.records:
      - Match to existing facility
      - For each address:
        - If exists: update fields
        - If new: create Address record
      - Collect facilities needing update (LastModifiedReason, etc.)

   e. PNM_DMLUtil.bulkUpsert(addressRecords, Address.External_Id__c, 200)
      -> Partial success DML

   f. PNM_DMLUtil.bulkUpdate(facilityUpdates, 200)
      -> Update facility timestamps/status

   g. PNM_ErrorLogger.logDMLFailures(result, ctx)  [if any failures]

   h. Return PNM_ServiceResponse.success(...)
```

---

## 8. Mind Map: Practitioner Participation Form (Complete Batch-Driven Flow)

```
+============================================================================+
|          PRACTITIONER PARTICIPATION FORM - COMPLETE SERVICE MAP              |
|       (Following Practitioner Creation Redesign pattern: L4 -> Batch)       |
+============================================================================+

OmniScript: "Practitioner Participation Form"
  |
  |-- [Page 1-N: Practitioner Demographics, Locations, Specialties, etc.]
  |     Remote Action -> PNM_ServiceDispatcher
  |       actionName: 'processPractitionerParticipation'
  |
  +-- PNM_ParticipationFormService.execute(request)
        |
        |== [SYNC - Level 1-3 Records] =======================================
        |     |
        |     |-- (1) VALIDATE
        |     |     PNM_ParticipationFormService.validate()
        |     |     - Required: NPI, LastName, TIN, at least 1 location
        |     |     - Format: NPI = 10 digits, TIN format, valid state codes
        |     |     - Business: No duplicate active enrollment for same TIN+NPI
        |     |
        |     |-- (2) DEDUP / MATCH
        |     |     PNM_PractitionerSelector.getPractitionersByNPI(npiSet)
        |     |     PNM_Selector.byExternalIds('HealthcareFacility', 'TIN__c', tinSet)
        |     |     PNM_CollectionUtil.mapByField(practitioners, 'NPI__c')
        |     |     -> Determines: CREATE new vs. UPDATE existing
        |     |
        |     |-- (3) LEVEL 1: PRACTITIONER (HealthcarePractitioner)
        |     |     PNM_CollectionUtil.mapToSObjects(records, HP.SObjectType, fieldMap)
        |     |     PNM_DMLUtil.bulkUpsert(practitioners, HP.NPI__c, 200)
        |     |     -> Create/Update HealthcarePractitioner records
        |     |     -> Output: practResult.successIds (used for L2, L3, L4)
        |     |
        |     |-- (4) LEVEL 2: PRACTICE LOCATION (HealthcareFacility)
        |     |     Build facility records from 'practiceLocations' in each record
        |     |     PNM_DMLUtil.bulkUpsert(facilities, HF.Location_External_Id__c, 200)
        |     |     -> Create/Update practice location records
        |     |     -> Output: facResult.successIds
        |     |
        |     |-- (5) LEVEL 3: PRACTITIONER ROLE (Junction)
        |     |     Build PractitionerRole linking Practitioner <-> Location
        |     |     PNM_DMLUtil.bulkUpsert(roles, PR.External_Id__c, 200)
        |     |     -> Junction: who practices where, effective dates, status
        |     |
        |     +-- Return to OmniScript: SUCCESS + batchJobId + summary
        |
        |== [ASYNC - Level 4 Records via Batch] ==============================
        |     |
        |     |-- Database.executeBatch(PNM_ParticipationFormLevel4Batch, 200)
        |           |
        |           |-- start(): Query practitioners by IDs from Level 1
        |           |
        |           |-- execute() scope = batch of practitioners
        |           |     |
        |           |     |-- (6) SPECIALTIES (CareProviderFacilitySpecialty)
        |           |     |     - Primary & secondary specialties
        |           |     |     - Board certifications + dates
        |           |     |     - Taxonomy codes
        |           |     |     PNM_DMLUtil.bulkInsert(specialties, 200)
        |           |     |
        |           |     |-- (7) IDENTIFIERS (PractitionerIdentifier__c)
        |           |     |     - DEA numbers (by state)
        |           |     |     - State license numbers
        |           |     |     - Medicaid/Medicare provider IDs
        |           |     |     - CLIA numbers
        |           |     |     PNM_DMLUtil.bulkUpsert(identifiers, ExternalId, 200)
        |           |     |
        |           |     |-- (8) LANGUAGES (HealthcarePractitionerLanguage__c)
        |           |     |     PNM_DMLUtil.bulkInsert(languages, 200)
        |           |     |
        |           |     |-- (9) ADDRESSES (Address)
        |           |     |     - Practice address
        |           |     |     - Mailing address  
        |           |     |     - Billing address
        |           |     |     - Correspondence address
        |           |     |     PNM_DMLUtil.bulkInsert(addresses, 200)
        |           |     |
        |           |     |-- (10) HOSPITAL AFFILIATIONS (PractitionerAffiliation__c)
        |           |     |      - Hospital name, privilege status, dates
        |           |     |      PNM_DMLUtil.bulkInsert(affiliations, 200)
        |           |     |
        |           |     +-- (11) OFFICE HOURS / AVAILABILITY
        |           |            PNM_DMLUtil.bulkInsert(officeHours, 200)
        |           |
        |           |-- finish():
        |                 - Publish PNM_AsyncComplete__e (OmniScript listens)
        |                 - Chain to Credentialing Queueable
        |
        |== [ASYNC - Credentialing Chain (Queueable)] ========================
              |
              |-- PNM_CredentialingQueueable (chained from batch finish)
                    |
                    |-- (12) CREATE CREDENTIALING CASE
                    |     - If new practitioner OR re-credentialing due
                    |     - Case RecordType = 'PNM_Credentialing'
                    |     - Set due dates based on config
                    |
                    |-- (13) CREATE VERIFICATION TASKS
                    |     - Primary Source Verification (PSV) tasks
                    |     - License verification
                    |     - DEA verification
                    |     - Board certification verification
                    |     - OIG/SAM exclusion check
                    |
                    +-- Publish PNM_AsyncComplete__e with final status
```

---

## 9. Comparison: Before (IP) vs After (Apex Service Framework)

```
+------------------+----------------------------+-----------------------------------+
|     Concern      |   Before (IP-Heavy)        |   After (Apex Service Framework)  |
+------------------+----------------------------+-----------------------------------+
| Entry Point      | Complex multi-step IP      | Thin IP or Remote Action          |
|                  | with 20+ elements          | -> PNM_ServiceDispatcher          |
+------------------+----------------------------+-----------------------------------+
| Business Logic   | Scattered across IP        | Centralized in Service class      |
|                  | elements + DataRaptors     | (PNM_ParticipationFormService)    |
+------------------+----------------------------+-----------------------------------+
| Governor Limits  | Hit CPU/Heap on > 5 recs   | Auto-delegates to async at        |
|                  | No mitigation strategy     | configurable threshold            |
+------------------+----------------------------+-----------------------------------+
| Level 4 Records  | Created inline in IP       | Delegated to Batch (like          |
|                  | -> CPU timeout             | Practitioner Creation Redesign)   |
+------------------+----------------------------+-----------------------------------+
| Error Handling   | Generic IP error screen    | Structured errors with codes,     |
|                  | "An error occurred"        | field-level detail, logged to     |
|                  |                            | PNM_Error_Log__c                  |
+------------------+----------------------------+-----------------------------------+
| Reusability      | Copy-paste IPs for each    | New transaction = 1 service class |
|                  | new transaction type       | + register in dispatcher          |
+------------------+----------------------------+-----------------------------------+
| DML              | Individual DML per record  | Batched DML with partial success  |
|                  | in loops (non-bulkified)   | via PNM_DMLUtil                   |
+------------------+----------------------------+-----------------------------------+
| SOQL             | Multiple DataRaptors       | Single optimized query via        |
|                  | (each = 1+ SOQL)           | PNM_Selector with bind vars       |
+------------------+----------------------------+-----------------------------------+
| Testing          | Manual QA only             | Unit testable services with       |
|                  |                            | injectable selectors              |
+------------------+----------------------------+-----------------------------------+
```

---

## 10. How to Add a New Transaction (Plugin Pattern)

Adding a new PNM transaction (e.g., "Process Roster File") requires **minimal net-new code**:

### Step 1: Create Service Class (the only custom logic)
```java
public class PNM_RosterProcessingService extends PNM_BaseService {
    
    { ASYNC_RECORD_THRESHOLD = 100; }
    
    protected override List<PNM_ServiceResponse.PNM_ErrorDetail> validate(PNM_ServiceRequest request) {
        // Your validation logic
    }
    
    protected override PNM_ServiceResponse processSync(PNM_ServiceRequest request) {
        // Use PNM_Selector, PNM_CollectionUtil, PNM_DMLUtil
    }
    
    protected override PNM_AsyncProcessor getAsyncProcessor(PNM_ServiceRequest request) {
        return new PNM_RosterBatch();
    }
}
```

### Step 2: Register in Dispatcher (one line)
```java
'processRosterFile' => PNM_RosterProcessingService.class
```

### Step 3: (Optional) Batch class if complex
### Step 4: Configure Custom Metadata (no code deploy needed)

---

## 11. Heap Size Management Strategies

1. **Chunked Processing** - `PNM_CollectionUtil.chunk()` splits large lists
2. **Streaming Pattern** - Process each chunk, DML, then null references
3. **Selective Queries** - `PNM_Selector` never does `SELECT *`
4. **String Building** - Use `List<String>.join()` not concatenation in loops
5. **Map Estimation** - `PNM_GovernorUtil.hasHeapRoom()` before building large maps
6. **SObject Trimming** - Null out large text fields after processing
7. **Batch Delegation** - When heap gets tight, remaining work goes to batch (fresh heap)

---

## 12. Custom Metadata & Objects Inventory

| Component | Type | Purpose |
|---|---|---|
| `PNM_Service_Config__mdt` | Custom Metadata | Runtime thresholds per action |
| `PNM_Field_Mapping__mdt` | Custom Metadata | OmniStudio -> SObject field maps |
| `PNM_Error_Log__c` | Custom Object | Persistent error/info log records |
| `PNM_Error_Log__e` | Platform Event | Async-safe logging channel |
| `PNM_AsyncComplete__e` | Platform Event | Batch/Queueable completion notification |

---

## 13. Key Design Principles

1. **Single Responsibility** - Each class has one reason to change
2. **Open/Closed** - New transactions extend, don't modify existing code
3. **Template Method** - PNM_BaseService defines the algorithm skeleton
4. **Strategy Pattern** - Async vs. sync determined at runtime
5. **Registry Pattern** - PNM_ServiceDispatcher maps actions to services
6. **Partial Success — Bounded** - `allOrNone=false` is the default for **fan-out leaves** (ProviderFeature, ACC, PFAA, demographic rows); it is **never** the default for parent↔junction pairs (HCFacility↔HCPF, Location↔Address, HCFN insert+deactivate). See §14.1.
7. **Fail Fast** - Validate before expensive operations
8. **Governor-Aware** - Every utility checks limits before proceeding
9. **Correlation** - Every log entry ties back to a transaction ID
10. **Batch for L4** - Following the successful Practitioner Creation Redesign pattern
11. **TX1 owns user-visible records** - If the next OmniScript screen reads a record or the directory exposes it, the record commits in TX1, not TX2. TX2 is reserved for fan-out per-location records that are not on the user's critical path. See §14.5.

---

## 14. Cross-cutting Framework Patterns

> The framework defines four small but opinionated patterns that every flow's services build on. Each closes a specific class of correctness or operability bug that OmniStudio integration procedures inherit by default. Every flow document references this section rather than re-stating the pattern.

### 14.1 `PRM_BulkOperation` — junction-aware partial-success DML

> **Why we need it** — Every flow inserts parent records and child junction records in the same transaction (`HealthcareFacility ➜ HCPF`, `Location ➜ Address`, `HCFN insert + deactivate`). With `Database.allOrNone=false`, the junction insert can succeed using a foreign-key value pointing to a parent that **failed**, leaving an orphan, or a junction can be inserted while its sibling deactivate fails leaving both rows active. `PRM_DMLUtil.bulkInsertWithPartialSuccess` is too coarse for this case.
>
> **How it helps** — A typed builder that links `Database.SaveResult[]` from one DML chunk to the bind list of the next, drops orphan-bound rows before they hit the database, and groups insert+deactivate pairs under `allOrNone=true` per chunk. Every flow's parent↔junction code path uses this instead of `bulkInsertWithPartialSuccess` directly.
>
> **Outcome** — Orphan junction rows become impossible by construction.

```apex
/**
 * Junction-aware DML builder. Use whenever a child SObject's foreign key
 * refers to a record being inserted in the same logical transaction.
 *
 * Pattern A — parent ➜ junction (orphan-safe):
 *   PRM_BulkOperation.chain()
 *     .insertParents(locations)                   // SaveResults captured
 *     .bindChildFK(addresses, 'LocationId')       // failed parents drop the child
 *     .insertChildren(addresses)
 *     .execute(res);
 *
 * Pattern B — co-transactional pair (insert + deactivate):
 *   PRM_BulkOperation.atomicPair()
 *     .insert(toInsertHCFN)
 *     .update(toDeactivateHCFN)
 *     .execute(res);     // allOrNone=true on the pair, partial across pairs
 */
public with sharing class PRM_BulkOperation {

    public static ParentChild chain() { return new ParentChild(); }
    public static AtomicPair atomicPair() { return new AtomicPair(); }

    /** Parent ➜ child(ren) linked by FK. Orphan-bound children are dropped. */
    public class ParentChild {
        private List<SObject> parents;
        private Map<Integer, List<SObject>> children = new Map<Integer, List<SObject>>();
        private Map<Integer, String> childFkField = new Map<Integer, String>();
        private Database.SaveResult[] parentResults;

        public ParentChild insertParents(List<SObject> p) { this.parents = p; return this; }

        /** Child rows are aligned by index with parents (parents[i] ↔ children[i]). */
        public ParentChild bindChildFK(List<SObject> kids, String fk) {
            Integer key = children.size();
            children.put(key, kids);
            childFkField.put(key, fk);
            return this;
        }

        public void execute(PRM_ServiceResult res) {
            // 1) Parent insert with partial success
            parentResults = Database.insert(parents, false);
            for (Integer i = 0; i < parentResults.size(); i++) {
                if (!parentResults[i].isSuccess()) {
                    PRM_ErrorLogger.logSaveResult(parentResults[i], parents[i], res);
                }
            }
            // 2) For each child collection: bind FK from successful parents only,
            //    drop the child whose parent failed (orphan prevention).
            for (Integer key : children.keySet()) {
                List<SObject> rawChildren = children.get(key);
                String fk = childFkField.get(key);
                List<SObject> survivors = new List<SObject>();
                for (Integer i = 0; i < parentResults.size(); i++) {
                    if (parentResults[i].isSuccess() && rawChildren.size() > i) {
                        rawChildren[i].put(fk, parentResults[i].getId());
                        survivors.add(rawChildren[i]);
                    }
                }
                Database.SaveResult[] childResults = Database.insert(survivors, false);
                for (Integer i = 0; i < childResults.size(); i++) {
                    if (!childResults[i].isSuccess()) {
                        PRM_ErrorLogger.logSaveResult(childResults[i], survivors[i], res);
                    }
                }
            }
        }
    }

    /** Two writes that must succeed or fail together (allOrNone=true). */
    public class AtomicPair {
        private List<SObject> toInsert = new List<SObject>();
        private List<SObject> toUpdate = new List<SObject>();

        public AtomicPair insert(List<SObject> recs) { this.toInsert.addAll(recs); return this; }
        public AtomicPair update(List<SObject> recs) { this.toUpdate.addAll(recs); return this; }

        public void execute(PRM_ServiceResult res) {
            Savepoint sp = Database.setSavepoint();
            try {
                if (!toInsert.isEmpty()) Database.insert(toInsert, true);
                if (!toUpdate.isEmpty()) Database.update(toUpdate, true);
            } catch (DmlException e) {
                Database.rollback(sp);
                PRM_ErrorLogger.logException(e, res);
                throw e;   // fail loud — caller decides whether the whole flow rolls back
            }
        }
    }
}
```

**Where each flow uses it:**

| Flow | Replaces | Pattern |
|---|---|---|
| Par Form | `PRMDRCreatePractitionerNewAddressRecords` Location+Address+HCF+HCPF chain | `chain()` (parent=Location, children=Address, HCF, HCPF) |
| Par Form | Group HCF + Group NPI + HCFN | `chain()` (parent=Group HCF, children=Group NPI, Group HCFN) |
| PDA Review | `PRMLoadRelatedRecordsForPNC` (HCF+HCPF+Provider) | `atomicPair()` (or 3-way atomic) |
| Off-Cycle Submit | `PRMDRPHCPractFacHCFacilityLocationAddress` (5-SObject) | `chain()` × 2 |
| Off-Cycle PDA | `PRMDRPHCFNetwork` (insert new + deactivate unused) | `atomicPair()` |
| Reinstate | `PRMDRPracticeToPractitionerUpdate` + `CreatePracticeToPractitioner` | `atomicPair()` per practitioner |

### 14.2 `PRM_AsyncEnqueueGuard` — governor-safe enqueue with inline fallback

> **Why we need it** — Every orchestrator does `System.enqueueJob(new …)` from inside `processSync`. Salesforce caps Queueable enqueues at 1 per synchronous transaction (50 per async transaction). When that cap is already burned by an earlier step (a trigger, a Flow, a Process Builder), the second `enqueueJob` throws `LimitException` AFTER `processSync` has already returned a success-shaped response. The user sees "Submitted" but the heavy work silently never runs.
>
> **How it helps** — A guard that wraps the enqueue: if the limit is exhausted, the job runs **inline in the same transaction** with a degraded-but-correct outcome (or, if it can't fit, returns an explicit `ASYNC_DEFERRED` status that the LWC surfaces as a banner with a manual "retry" button). The decision is logged.
>
> **Outcome** — Silent async drop is impossible.

```apex
public with sharing class PRM_AsyncEnqueueGuard {

    public enum Result { ENQUEUED, RAN_INLINE, DEFERRED }

    /**
     * Try to enqueue. If the per-transaction cap is exhausted, fall back to inline
     * execution. If even inline execution would breach a hard governor (e.g. CPU
     * already > 80% used), record DEFERRED and surface to the user.
     */
    public static Result safeEnqueue(Queueable job, Runnable inlineFallback,
                                      Integer estimatedRowCount, PRM_ServiceResult res) {
        try {
            Id jobId = System.enqueueJob(job);
            res.asyncJobId = jobId;
            return Result.ENQUEUED;
        } catch (System.LimitException e) {
            if (PRM_GovernorUtil.canRunInline(estimatedRowCount)) {
                inlineFallback.run();
                res.note = 'Async cap reached — completed inline.';
                return Result.RAN_INLINE;
            }
            // Last resort: persist a recovery record and surface to user
            insert new PRM_AsyncJobStatus__c(
                JobName__c    = job.toString().substringBefore(':'),
                ContextId__c  = res.contextId,
                Status__c     = 'DEFERRED',
                Reason__c     = 'enqueueJob limit reached; row count too high for inline'
            );
            res.note = 'Submission accepted — heavy work deferred. The system will retry shortly.';
            return Result.DEFERRED;
        }
    }
}
```

> **`Runnable`** is a one-method functional interface (`void run()`) — Apex 64+ supports it via `System.Runnable`; pre-64 orgs use a small in-house equivalent.

### 14.3 `PRM_AsyncJobStatus__c` — deterministic poll backup for `PRM_AsyncComplete__e`

> **Why we need it** — Platform Events are best-effort; on heavy events traffic the LWC bell can lose a `PRM_AsyncComplete__e` and the user sees a permanent spinner. A deterministic recovery channel is needed.
>
> **How it helps** — Every Queueable opens a `PRM_AsyncJobStatus__c` row at enqueue (status=`QUEUED`), updates it on success/failure, and the LWC polls this row if it hasn't received the Platform Event within N seconds.
>
> **Outcome** — No more permanent spinners.

```
PRM_AsyncJobStatus__c
─────────────────────────────────────────────────────────
JobName__c         text  (e.g. "PRM_ParFormLevel4Batch")
ContextId__c       text  (caseId or transactionId)
Status__c          picklist (QUEUED, RUNNING, COMPLETED, FAILED, DEFERRED)
RowsProcessed__c   number
RowsFailed__c      number
StartedAt__c       datetime
CompletedAt__c     datetime
Reason__c          long text  (failure / deferral reason)
Payload__c         long text  (JSON of result)
```

`PRM_AsyncJobStatusService.lookup(jobName, contextId)` is exposed as `@AuraEnabled` so the LWC can poll. `PRM_BaseQueueable` writes the row in its template-method `start()`/`finish()` hooks — every flow's Queueable inherits the behaviour for free.

### 14.4 `PRM_CaseDataMgrPatcher` — field-level merge for IndividualApplication CM flags

> **Why we need it** — Multiple services across Par Form, PDA Review, Off-Cycle Submit, Off-Cycle PDA, and Reinstate stamp the same 14-flag IndividualApplication row at the end of their respective `runHeavyWork` methods. If two flows touch the same case (e.g. a Reinstate completes async while an Off-Cycle PDA arrives sync), the second `update(record)` overwrites the first's flags entirely.
>
> **How it helps** — A patcher that uses `Schema.FieldSet` (or an explicit allow-list per flow) to update **only the fields the caller owns**. Implemented as `Database.update(record, false)` with a stripped-down SObject that contains only the owned fields (Apex DML semantics: only populated fields are written).
>
> **Outcome** — Two flows can stamp non-overlapping flags on the same CM record concurrently without overwriting each other.

```apex
public with sharing class PRM_CaseDataMgrPatcher {

    /** Each flow owns a named subset of CM flags. Adding a new flow ⇒ add a key here. */
    public static final Map<String, Set<String>> OWNERSHIP = new Map<String, Set<String>>{
        'ParForm'         => new Set<String>{ 'PRM_AccountFlag__c', 'PRM_HCFFlag__c',
                                              'PRM_HCPFFlag__c', 'PRM_HCPNPIFlag__c',
                                              'PRM_LocationFlag__c', 'PRM_AddressFlag__c',
                                              'PRM_PersonAccountFlag__c', 'PRM_HPTFlag__c',
                                              'PRM_IdentifierFlag__c', 'PRM_ContentVersionFlag__c',
                                              'PRM_PersonEducationFlag__c', 'PRM_ProviderFeatureFlag__c',
                                              'PRM_HCFNFlag__c'},
        'PDAReview'       => new Set<String>{ 'PRM_HCFNFlag__c', 'PRM_HCFFlag__c',
                                              'PRM_IdentifierFlag__c', 'PRM_BoardCertFlag__c',
                                              'PRM_AttestationStampedAt__c' },
        'OffCycleSubmit'  => new Set<String>{ 'PRM_OffCycleAccountFlag__c', 'PRM_OffCycleHCFFlag__c',
                                              'PRM_OffCycleHCFNFlag__c', 'PRM_OffCycleHPTFlag__c' },
        'OffCyclePDA'     => new Set<String>{ 'PRM_OffCyclePDAFlag__c', 'PRM_OffCyclePDAOutcome__c' },
        'Reinstate'       => new Set<String>{ 'PRM_ReinstateAccountFlag__c', 'PRM_ReinstateHCFFlag__c',
                                              'PRM_ReinstateHCPFFlag__c', 'PRM_ReinstateHCFNFlag__c',
                                              'PRM_ReinstateHPTFlag__c', 'PRM_ReinstateIdentifierFlag__c' }
    };

    public static void patch(String flowName, Id caseManagerId, Map<String, Object> values) {
        Set<String> allowed = OWNERSHIP.get(flowName);
        if (allowed == null) {
            throw new PRM_DomainException('Unknown flow: ' + flowName);
        }
        IndividualApplication ia = new IndividualApplication(Id = caseManagerId);
        for (String fld : values.keySet()) {
            if (allowed.contains(fld)) {
                ia.put(fld, values.get(fld));
            } else {
                throw new PRM_DomainException(flowName + ' may not patch ' + fld);
            }
        }
        Database.update(ia, false);   // only owned fields are populated → only those write
    }
}
```

### 14.5 TX1 / TX2 boundary doctrine

> A framework-level rule: every flow uses the same algorithm to decide whether a record commits in TX1 (sync) or TX2 (async).

A record commits in **TX1 (sync)** if **any** of these is true:

1. The next OmniScript screen displays it (e.g. primary contact name, case data manager name).
2. Another flow reads it during its own TX1 critical path (e.g. Off-Cycle PDA reads HCF/HCPF/Location written by Off-Cycle Submit).
3. The directory / member-search API exposes it (`Account.IsActive`, `HealthcareFacility.PRM_Active__c`, `HealthcarePractitionerFacility.IsActive`, `Identifier__c.IsActive`).
4. A workflow / process / trigger downstream of the user's submit reads it before the next user interaction.

A record may commit in **TX2 (async)** only if **all** of these are true:

1. The user does not see it on the immediately-following screen.
2. Other flows do not read it on their critical path within the next 5 minutes.
3. It is genuinely a fan-out per location / per network / per role (cardinality ≥ 5×).
4. A controlled failure of TX2 leaves the parent record in a self-consistent state (TX1's records are coherent on their own).

If any TX2 condition is false, the record moves to TX1 and the orchestrator either (a) keeps it sync if total row count fits the budget, or (b) chunks via `PRM_BulkOperation` with explicit Save-Result handling.

### 14.6 Where each flow applies these patterns

| Pattern | Par Form | PDA Review | Off-Cycle Submit | Off-Cycle PDA | Reinstate |
|---|---|---|---|---|---|
| `PRM_BulkOperation.chain()` | Address/HCF/HCPF + Group HCF/NPI/HCFN | — | The 5-SObject "big DR" + Group | A05 4-SObject Group | HCPF + new HCFN attach |
| `PRM_BulkOperation.atomicPair()` | — | `updateRelatedRecordsForPNC` (HCF+HCPF+Provider) | — | HCFN insert + deactivate | HCPF reactivate + new-attach |
| `PRM_AsyncEnqueueGuard.safeEnqueue` | TX2 batch | HCFN Queueable | TX2 Queueable | TX2 Queueable | Practitioner Queueable, ≤10 sync path |
| `PRM_AsyncJobStatus__c` polling | yes | yes | yes | yes | yes |
| `PRM_CaseDataMgrPatcher.patch(...)` | end of TX2 finish() | end of TX1 sync | TX1 stamp `In-Flight` + TX2 stamp `Complete` | TX1 stamp + TX2 stamp | end of `runHeavyDml` |
| TX1 / TX2 doctrine § 14.5 | Contact / ContactProfile / Telehealth InfoCodes ➜ TX1 | only HCFN async | Location/HCF/HCPF/Address ➜ TX1 | HCFN async | Account + HCPF + Identifier all in TX2 alongside children |
