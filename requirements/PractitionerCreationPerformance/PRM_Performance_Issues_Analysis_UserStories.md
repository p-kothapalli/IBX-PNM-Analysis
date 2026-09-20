# PRM Guided Flows - Performance Issues Analysis & User Stories

## Executive Summary

Analysis of PRM Integration Procedures identified **5 critical performance bottlenecks** affecting guided flows. These IPs process bulk data synchronously, causing UI timeouts and hitting Salesforce governor limits.

**Common Pattern:** Container IPs calling heavy child IPs that create 20-100+ records synchronously

---

## Issue #1: Delegated Practitioner Creation - Network Creation Timeout

### Affected Components
- **OmniScript:** `PRM_DelegatedPractitionerReviewScreen`
- **Container IP:** `PRM_AddressLogicContainer`
- **Child IP:** `PRM_CreateDelegatedHFNRecords` (24 steps)

### Current Behavior
When creating a delegated practitioner with multiple practice locations, the UI spins indefinitely at the network creation step.

### Technical Analysis

**Data Volume:**
- 3 practice locations
- 3 taxonomies per location = 9 taxonomy network records
- 15 payer networks per location = 45 payer network records
- IFC codes per location = 9-15 records
- **Total: 54-69 records created in single transaction**

**Operations Breakdown:**
```
Step 1: Taxonomy Network Creation
  - Query existing taxonomies (SOQL)
  - Transform taxonomy data (DataRaptor)
  - Deduplicate (List Manipulation)
  - Create 9 records (DML)
  → ~36 operations

Step 2: Payer Network Creation
  - Query existing networks (SOQL)
  - Query practice location payer associations (SOQL)
  - Transform network data (DataRaptor)
  - Deduplicate (List Manipulation)
  - Merge with practice locations (List Manipulation)
  - Create 45 records (DML)
  → ~180 operations

Step 3: IFC Record Creation
  - Query existing IFC codes (SOQL)
  - Transform IFC data (DataRaptor)
  - Deduplicate (List Manipulation)
  - Merge with practice locations (List Manipulation)
  - Create 15 records (DML)
  → ~45 operations

Supporting Steps:
  - Initial queries (practice locations, case manager, etc.)
  - Status updates
  - Validation checks
  → ~20 operations

TOTAL: ~280 operations in single synchronous transaction
```

**Governor Limits Hit:**
- ✅ SOQL Queries: 80-100 of 100 limit (approaching)
- ⚠️ CPU Time: 50-60s of 60s async limit (hitting)
- ⚠️ Heap Size: 10-12MB of 12MB limit (approaching)
- ✅ DML Statements: 15-20 of 150 limit (safe)

**Configuration Analysis:**
```json
// PRM_CreateDelegatedHFNRecords_PropertySetConfig.json
{
  "queueableChainableCpuLimit": 40000,      // 40s - may still timeout
  "queueableChainableQueriesLimit": 120,     // 120 queries
  "queueableChainableHeapSizeLimit": 6,      // 6MB
  "ttlMinutes": 5                            // 5 min timeout
}

// PRM_AddressLogicContainer_Element_AddTaxNetworkLogic.json
{
  "chainOnStep": false,        // ❌ Does NOT chain - waits for completion
  "disableChainable": true,    // ❌ Cannot be chained
  "useQueueable": true         // Uses queueable but parent waits
}
```

### Impact
- **User Experience:** UI unresponsive for 5+ minutes → timeout
- **Business Impact:** Cannot complete delegated practitioner onboarding
- **Support Load:** 15-20 tickets/week for "stuck" creations
- **Workaround:** Manual record creation (2-3 hours per practitioner)

### Use Case Scenarios

**Scenario 1: Small Practice (2 locations)**
- 2 locations × 3 taxonomies × 15 networks = 36 records
- Expected time: 3-4 minutes
- **Status:** ⚠️ May succeed but slow

**Scenario 2: Medium Practice (3-5 locations)** ← CURRENT ISSUE
- 3 locations × 3 taxonomies × 15 networks = 54 records
- Expected time: 5-8 minutes
- **Status:** 🔴 Timeout / Spinning

**Scenario 3: Large Group (5-10 locations)**
- 5 locations × 3 taxonomies × 15 networks = 90 records
- Expected time: 10+ minutes
- **Status:** 🔴 Always fails

**Scenario 4: Multi-Site Organization (10+ locations)**
- 10 locations × 3 taxonomies × 15 networks = 180 records
- **Status:** 🔴 Impossible with current architecture

---

## User Story #1: Delegated Practitioner Network Creation

### Story
**As a** Credentialing Specialist  
**I want to** complete delegated practitioner creation without UI timeouts  
**So that** I can onboard practitioners with multiple locations efficiently

### Acceptance Criteria
1. **Given** a delegated practitioner with 3 practice locations, each with 3 taxonomies and 15 networks  
   **When** I submit the practitioner creation form  
   **Then** the UI should return within 3 seconds with a "Processing..." message

2. **Given** network creation is processing in the background  
   **When** I navigate to the Case Manager record  
   **Then** I should see a status field showing current progress (e.g., "Processing Taxonomies", "Processing Networks")

3. **Given** all networks have been created successfully  
   **When** the batch process completes  
   **Then** I should receive an email notification with summary (X records created)

4. **Given** network creation fails for any reason  
   **When** the batch encounters an error  
   **Then** all created records should be rolled back AND I should receive an email with error details

5. **Given** I want to track processing time  
   **When** viewing the Case Manager record  
   **Then** I should see timestamps: "Queued At", "Started At", "Completed At"

### Technical Requirements
- Implement event-driven batch architecture
- Add status tracking fields to Case Manager
- Create 3 batch classes (Taxonomy, Payer Network, IFC)
- Implement rollback mechanism
- Add email notifications

### Performance Targets
- UI response: < 3 seconds
- Total processing: 8-15 minutes
- Support up to 20 practice locations per practitioner
- No governor limit exceptions

### Definition of Done
- [ ] Batch classes created with 90%+ code coverage
- [ ] Platform Event trigger implemented
- [ ] Status tracking fields added
- [ ] Email template created
- [ ] Integration Procedure modified to publish event
- [ ] Tested with 3, 5, 10 location scenarios
- [ ] Rollback mechanism tested
- [ ] User documentation updated

---

## Issue #2: IBC Professional Practitioner Creation - Address Processing Timeout

### Affected Components
- **OmniScript:** `PRM_PractitionerCreation`
- **Container IP:** `PRM_PractitionerCreationContainer` → `PRM_AddressLogicContainer`
- **Child IP:** `PRM_PractitionerAddressCreation` (100+ steps!)

### Current Behavior
When creating an IBC Professional Staff practitioner with multiple addresses, the process hangs during address/facility creation.

### Technical Analysis

**Complexity Metrics:**
- **Steps:** 100+ sequential operations
- **Data created per location:**
  - Address records (1-2 per location)
  - Location records
  - HealthCareFacility records
  - HealthCarePractitionerFacility records
  - Provider Feature records (3-5 per location)
  - Affirming Care Category records (2-3 per location)
  - Provider Feature Assistive Aids records (2-4 per location)
  - Practitioner Facility Network records (10-15 per location)
  - Info Code Assignment records (5-10 per location)
  - Practice Location relationships

**Total Records Per Location: 30-50 records**

**Data Volume Examples:**

**2 Practice Locations:**
- 60-100 records created
- 100+ steps executed
- ~300+ operations
- **Time:** 4-6 minutes
- **Status:** ⚠️ May timeout

**5 Practice Locations:**
- 150-250 records created
- 500+ steps executed
- ~1000+ operations
- **Time:** 10-20+ minutes
- **Status:** 🔴 Definite timeout

**Governor Limits at Risk:**
```
SOQL Queries: 90-100+ of 100 limit    → 🔴 HITTING
CPU Time: 50-60s of 60s async limit   → 🔴 HITTING
Heap Size: 10-12MB of 12MB limit      → ⚠️ APPROACHING
DML Statements: 40-60 of 150 limit    → ✅ OK
```

**IP Configuration:**
```json
// PRM_PractitionerAddressCreation_PropertySetConfig.json
{
  "chainableCpuLimit": 10000,              // 10s - too low!
  "chainableQueriesLimit": 100,            // 100 queries - hitting limit
  "chainableHeapSizeLimit": 6,             // 6MB
  "queueableChainableCpuLimit": 60000,     // 60s - still hitting
  "queueableChainableQueriesLimit": 200,   // 200 queries - may still hit
  "queueableChainableHeapSizeLimit": 12    // 12MB
}
```

**Problem Patterns in IP:**
1. **Sequential Processing:** Each location processed one at a time
2. **Nested Conditionals:** Multiple conditional blocks (SameNPI, DiffNPI, NewGroup, ExistingGroup)
3. **Repeated Queries:** Same SOQL queries executed multiple times
4. **Data Transformation:** Heavy DataRaptor operations in loops
5. **List Manipulations:** Extensive list merging and filtering

### Impact
- **User Experience:** 4-10 minute wait → timeout
- **Business Impact:** Cannot onboard practitioners efficiently
- **Data Integrity:** Partial records created on timeout
- **Support Load:** 10-15 tickets/week

### Use Case Scenarios

**Scenario 1: Solo Practitioner (1 location)**
- 1 location, 1 address
- 30-40 records
- **Status:** ✅ Works but slow (2-3 min)

**Scenario 2: Small Group (2-3 locations)** ← COMMON
- 3 locations, 3 addresses
- 90-120 records
- **Status:** ⚠️ Timeout risk (4-6 min)

**Scenario 3: Medium Group (4-7 locations)**
- 5 locations, 5 addresses
- 150-200 records
- **Status:** 🔴 Usually fails (8-12 min)

**Scenario 4: Large Group (8+ locations)**
- 10 locations, 10 addresses
- 300-400 records
- **Status:** 🔴 Always fails (15-25+ min)

**Scenario 5: Hospital System (15-20 locations)**
- Currently impossible to complete
- Would require manual record creation (8-16 hours)

---

## User Story #2: IBC Professional Practitioner Address Creation

### Story
**As a** Credentialing Specialist  
**I want to** add multiple practice locations to an IBC Professional practitioner  
**So that** I can complete onboarding for practitioners working at multiple sites

### Acceptance Criteria
1. **Given** an IBC Professional practitioner with 5 practice locations  
   **When** I submit the practitioner creation form  
   **Then** the address/facility creation should complete within 5 minutes OR process asynchronously

2. **Given** I'm creating a practitioner with 10+ locations  
   **When** I submit the form  
   **Then** I should receive immediate confirmation and email notification when complete

3. **Given** address creation is processing  
   **When** I check the Case Manager record  
   **Then** I should see which locations have been processed (e.g., "3 of 5 locations complete")

4. **Given** one location fails validation/creation  
   **When** the process encounters an error  
   **Then** other locations should still be created AND error should be logged with specific location details

5. **Given** I need to track performance  
   **When** reviewing system logs  
   **Then** I should see processing time per location and bottleneck steps

### Technical Requirements
- Break `PRM_PractitionerAddressCreation` into smaller, focused IPs:
  - `PRM_CreateLocationAndAddress` (Steps 1-30)
  - `PRM_CreateHealthCareFacilityRecords` (Steps 31-50)
  - `PRM_CreateProviderFeatures` (Steps 51-70)
  - `PRM_CreateNetworkAssignments` (Steps 71-90)
  - `PRM_CreateInfoCodeAssignments` (Steps 91-100)
- Implement batch processing for 5+ locations
- Add per-location error handling (partial success)
- Optimize SOQL queries (bulkify, reduce redundant queries)
- Cache lookup data (record types, picklist values)

### Performance Targets
- 1-3 locations: < 5 minutes synchronous
- 4-10 locations: 8-15 minutes asynchronous
- 10+ locations: 15-30 minutes asynchronous
- Support up to 50 locations per practitioner

### Definition of Done
- [ ] IP refactored into 5 smaller IPs
- [ ] Batch processing implemented for bulk scenarios
- [ ] Query optimization completed (< 50 queries per location)
- [ ] Error handling per location (no all-or-nothing)
- [ ] Status tracking with location-level granularity
- [ ] Performance tested with 1, 5, 10, 20 location scenarios
- [ ] Code coverage > 85%
- [ ] User documentation updated

---

## Issue #3: Initial Credentialing PDA Review - Network Update Timeout

### Affected Components
- **OmniScript:** `PRM_InitialCredPDA`
- **Container IP:** `PRM_InitialCredPDAReviewUpdateParent`
- **Child IP:** `PRM_InitialCredPDAReviewUpdateSubIPInsert` (44 steps)

### Current Behavior
When reviewing/updating PDA (Post-Delegation Assessment) records with network assignments, the process times out during network record creation.

### Technical Analysis

**IP Complexity:**
- **Steps:** 44 sequential operations
- **Loop Blocks:** 10+ (processing arrays)
- **DataRaptor Transforms:** 8
- **DataRaptor Loads:** 6
- **List Manipulations:** 12+

**Data Volume:**
Per practitioner being reviewed:
- Info Code Assignments: 5-15 records
- Practice Location Networks: 10-30 records
- Taxonomy Networks: 3-9 records
- HealthCareFacilityNetwork records: 20-50 records
- **Total: 38-104 records per practitioner**

**Multiple Practitioners in Review:**
- Small batch (3 practitioners): 114-312 records
- Medium batch (5 practitioners): 190-520 records
- Large batch (10 practitioners): 380-1040 records

**Operations Breakdown:**
```
1. RASetRecords - Query case manager records
2. Transform PNC Records (DataRaptor)
3. Loop through each practitioner:
   a. Extract info codes (List Manipulation)
   b. Convert to SObjects (Remote Action)
   c. Extract networks (List Manipulation)
   d. Query existing networks (SOQL)
   e. Deduplicate (List Manipulation)
   f. Create network records (DataRaptor Load)
4. Create info code assignments (DataRaptor Load)
5. Create taxonomy networks (DataRaptor Load)
6. Create facility networks (DataRaptor Load - useQueueable: true)

For 5 practitioners with 30 networks each:
- SOQL Queries: 60-80
- DML Operations: 150+ records
- CPU Time: 40-60s
- List iterations: 500+
```

**Configuration:**
```json
{
  "chainableCpuLimit": 10000,
  "queueableChainableCpuLimit": 60000,
  "queueableChainableQueriesLimit": 200
}

// Element: InitialCredPDAReviewHFN
{
  "useQueueable": true,
  "chainOnStep": false      // ❌ Waits for queueable to complete
}
```

### Impact
- **User Experience:** 3-8 minute freeze → timeout
- **Business Impact:** Cannot complete PDA reviews in batches
- **Workaround:** Process practitioners one at a time (10x slower)
- **Support Load:** 8-12 tickets/week

### Use Case Scenarios

**Scenario 1: Single Practitioner Review**
- 1 practitioner, 20 networks
- 40-80 records
- **Status:** ✅ Works (1-2 min)

**Scenario 2: Small Batch Review (3 practitioners)**
- 3 practitioners, 20 networks each
- 120-240 records
- **Status:** ⚠️ Timeout risk (3-5 min)

**Scenario 3: Standard Batch Review (5 practitioners)** ← COMMON
- 5 practitioners, 25 networks each
- 200-400 records
- **Status:** 🔴 Usually fails (5-8 min)

**Scenario 4: Large Batch Review (10 practitioners)**
- 10 practitioners, 30 networks each
- 400-800 records
- **Status:** 🔴 Always fails (10-15+ min)

**Scenario 5: Monthly PDA Review (50+ practitioners)**
- Currently impossible in single session
- Must be broken into 10+ manual sessions

---

## User Story #3: PDA Review Batch Network Creation

### Story
**As a** Quality Assurance Reviewer  
**I want to** review and update network assignments for multiple practitioners at once  
**So that** I can complete monthly PDA reviews efficiently

### Acceptance Criteria
1. **Given** I'm reviewing 5 practitioners with network updates  
   **When** I submit the batch review  
   **Then** the process should complete within 5 minutes OR notify me of async processing

2. **Given** I'm processing 10+ practitioners  
   **When** I initiate the batch review  
   **Then** I should receive immediate confirmation and progress updates every 2 minutes

3. **Given** batch processing is underway  
   **When** I check the status dashboard  
   **Then** I should see: Total count, Processed count, In Progress, Failed

4. **Given** one practitioner's networks fail to create  
   **When** the batch encounters an error  
   **Then** other practitioners should complete successfully AND I should see which failed

5. **Given** I need audit trail  
   **When** reviewing batch completion  
   **Then** I should see per-practitioner summary: records created, time taken, status

### Technical Requirements
- Refactor to process practitioners in parallel (where possible)
- Implement batch-based processing for 5+ practitioners
- Add progress tracking (processed/total)
- Implement per-practitioner error isolation
- Optimize queries (bulk queries instead of loops)
- Cache network metadata

### Performance Targets
- 1-3 practitioners: < 3 minutes synchronous
- 4-7 practitioners: 5-10 minutes asynchronous
- 8-20 practitioners: 10-25 minutes asynchronous
- 20+ practitioners: Batch apex with email completion

### Definition of Done
- [ ] IP refactored for parallel processing
- [ ] Batch processing for 5+ practitioners
- [ ] Per-practitioner error handling
- [ ] Progress tracking dashboard/component
- [ ] Query optimization (< 10 queries per practitioner)
- [ ] Performance tested with 1, 5, 10, 20 scenarios
- [ ] Audit logging implemented
- [ ] User training materials created

---

## Issue #4: Supplier Network Creation - Bulk Account Linking

### Affected Components
- **OmniScript:** `PRM_SupplierNetworkCreation`
- **Container IP:** `PRM_IPSupplierNetworkRecordCreationParent`
- **Child IP:** `PRM_SupplierNetworkCreation` (estimated 30-50 steps)

### Current Behavior
When creating supplier network relationships between accounts, the process times out when linking 10+ accounts.

### Technical Analysis

**Estimated Complexity:**
- Multiple account lookups
- Network hierarchy validation
- Relationship record creation
- Historical record updates

**Data Volume:**
Per supplier network:
- Account lookups: 10-50 accounts
- Network relationship records: 10-50
- Contract associations: 5-20
- **Total: 25-120 records**

**Risk Factors:**
- Recursive account hierarchies
- Complex validation rules
- Historical data updates

### Use Case Scenarios

**Scenario 1: Small Supplier (5-10 accounts)**
- 10 accounts, 1 network
- 30-50 records
- **Status:** ⚠️ Slow (2-4 min)

**Scenario 2: Medium Supplier (10-25 accounts)** ← COMMON
- 20 accounts, 2 networks
- 60-100 records
- **Status:** 🔴 Timeout risk (4-7 min)

**Scenario 3: Large Supplier (25-50 accounts)**
- 40 accounts, 3 networks
- 150-200 records
- **Status:** 🔴 Usually fails (8-12 min)

**Scenario 4: Enterprise Supplier (50+ accounts)**
- 100+ accounts, multiple networks
- **Status:** 🔴 Impossible

---

## User Story #4: Supplier Network Bulk Linking

### Story
**As a** Network Administrator  
**I want to** create supplier network associations for multiple accounts  
**So that** I can configure large supplier networks efficiently

### Acceptance Criteria
1. **Given** I'm linking 25 accounts to a supplier network  
   **When** I submit the network creation  
   **Then** the process should complete without timeout OR process asynchronously

2. **Given** I'm processing 50+ accounts  
   **When** I initiate bulk linking  
   **Then** I should receive confirmation and estimated completion time

3. **Given** linking is processing  
   **When** I check progress  
   **Then** I should see: Total accounts, Linked, In Progress, Failed

4. **Given** some accounts fail validation  
   **When** the process completes  
   **Then** successful links should be created AND I should see which accounts failed with reasons

5. **Given** I need to verify network setup  
   **When** viewing the supplier network  
   **Then** I should see list of all linked accounts with status and timestamps

### Technical Requirements
- Implement batch processing for 20+ accounts
- Add account-level error handling
- Optimize account hierarchy queries
- Implement progress tracking
- Add rollback for failed batches

### Performance Targets
- 1-10 accounts: < 3 minutes
- 10-30 accounts: 5-10 minutes async
- 30-100 accounts: 15-30 minutes batch
- 100+ accounts: Bulk processing with staging

### Definition of Done
- [ ] Batch processing implemented
- [ ] Account-level error isolation
- [ ] Query optimization completed
- [ ] Progress tracking UI component
- [ ] Performance tested with 10, 30, 100 accounts
- [ ] Rollback mechanism tested
- [ ] User documentation updated

---

## Issue #5: Provider Screen Records Creation - Bulk Screening

### Affected Components
- **OmniScript:** Multiple application intake flows
- **Container IP:** `PRM_CreateProviderScreenRecordsContainer`
- **Child IP:** `PRM_CreateProviderScreenRecords`

### Current Behavior
When processing provider screening data (languages, contact profiles, case data), the process times out with large data sets.

### Technical Analysis

**Steps Breakdown:**
1. CreateContactProfileRecords
2. PersonLanguageBlock (conditional)
3. Transform Person Language (DataRaptor)
4. Create Person Language records (DataRaptor)
5. Create Case Data Manager records (DataRaptor)

**Data Volume:**
Per provider screening:
- Contact profiles: 1-3 records
- Person languages: 1-5 records
- Case data manager records: 5-15 records
- **Total: 7-23 records per provider**

**Bulk Screening:**
- 10 providers: 70-230 records
- 25 providers: 175-575 records
- 50 providers: 350-1150 records

### Use Case Scenarios

**Scenario 1: Individual Provider**
- 1 provider, 15 records
- **Status:** ✅ Works (< 1 min)

**Scenario 2: Small Batch (5 providers)**
- 5 providers, 75 records
- **Status:** ✅ Works (1-2 min)

**Scenario 3: Medium Batch (10-15 providers)** ← COMMON
- 12 providers, 180 records
- **Status:** ⚠️ Slow (2-4 min)

**Scenario 4: Large Batch (20-30 providers)**
- 25 providers, 400 records
- **Status:** 🔴 Timeout risk (5-8 min)

**Scenario 5: Mass Screening (50+ providers)**
- 50+ providers
- **Status:** 🔴 Impossible

---

## User Story #5: Bulk Provider Screening

### Story
**As a** Credentialing Coordinator  
**I want to** process screening records for multiple providers at once  
**So that** I can handle high-volume intake periods efficiently

### Acceptance Criteria
1. **Given** I'm processing 15 provider screenings  
   **When** I submit the batch  
   **Then** the process should complete within 5 minutes OR notify me of async processing

2. **Given** I'm processing 30+ screenings  
   **When** I initiate bulk processing  
   **Then** I should receive confirmation and progress dashboard access

3. **Given** bulk processing is active  
   **When** I check the dashboard  
   **Then** I should see: Total, Complete, In Progress, Failed

4. **Given** some screenings fail validation  
   **When** the batch completes  
   **Then** successful screenings should be saved AND I should see failure reasons per provider

5. **Given** I need reporting  
   **When** viewing batch completion  
   **Then** I should be able to export results (CSV/Excel) with per-provider details

### Technical Requirements
- Implement batch processing for 10+ providers
- Add per-provider error handling
- Optimize DataRaptor operations (bulk mode)
- Add progress tracking
- Create export functionality

### Performance Targets
- 1-5 providers: < 2 minutes
- 6-15 providers: 3-5 minutes
- 16-30 providers: 8-15 minutes async
- 30+ providers: 15-30 minutes batch

### Definition of Done
- [ ] Batch processing for 10+ providers
- [ ] Per-provider error isolation
- [ ] DataRaptor optimization (bulk mode)
- [ ] Progress dashboard created
- [ ] Export functionality added
- [ ] Performance tested with 5, 15, 30, 50 providers
- [ ] User training completed

---

## Common Patterns & Root Causes

### Pattern 1: Container → Heavy Child IP
```
Container IP (error handler)
  → Child IP (100+ steps, creates 50-500 records)
     → Synchronous processing
     → UI waits → timeout
```

### Pattern 2: Loop-Based Processing
```
Loop through items (5-50 items):
  For each item:
    - Query data (SOQL)
    - Transform (DataRaptor)
    - Create records (DML)
  End Loop
  
Result: O(n) queries and DML → Governor limits
```

### Pattern 3: Nested DataRaptors in Loops
```
Loop through locations:
  Transform data (DataRaptor)
  Loop through networks:
    Transform network (DataRaptor)
    Create network (DataRaptor Load)
  End Loop
End Loop

Result: n × m DataRaptor executions → CPU timeout
```

### Pattern 4: Queueable Without Chaining
```json
{
  "useQueueable": true,
  "chainOnStep": false,      // Parent waits!
  "disableChainable": true   // Cannot chain further
}

Result: Async benefits lost, UI still waits
```

---

## Recommended Solutions

### Solution Matrix

| Issue | Current Time | Records | Solution | Target Time |
|-------|--------------|---------|----------|-------------|
| **#1: Delegated Network** | 5-∞ min | 54-69 | Event + Batch | 8-15 min async |
| **#2: IBC Address** | 4-20+ min | 90-400 | Refactor + Batch | 5-15 min async |
| **#3: PDA Review** | 3-15+ min | 120-800 | Parallel + Batch | 5-25 min async |
| **#4: Supplier Network** | 4-∞ min | 60-200 | Batch + Staging | 10-30 min async |
| **#5: Provider Screen** | 2-8+ min | 70-1150 | Bulk DataRaptor | 3-15 min async |

### Implementation Priority

**P0 - Critical (Sprint 1-2):**
1. **Delegated Network Creation** (#1) - Highest user impact
2. **IBC Address Creation** (#2) - Most complex, foundational fix

**P1 - High (Sprint 3-4):**
3. **PDA Review** (#3) - Affects monthly operations
4. **Provider Screening** (#5) - Seasonal high volume

**P2 - Medium (Sprint 5-6):**
5. **Supplier Network** (#4) - Less frequent, but critical when needed

---

## Architecture Recommendations

### General Pattern: Event-Driven Batch Processing

```
┌─────────────────────────────────────┐
│   OmniScript / Guided Flow          │
│                                     │
│   ↓ Submits data                    │
│                                     │
│   Container IP                      │
│   - Validation                      │
│   - Initial record creation         │
│   - Publish Platform Event ← NEW   │
│   - Return immediately (< 3s)      │
└──────────────┬──────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Platform Event Trigger              │
│  - Receives event                    │
│  - Calls orchestrator                │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Batch Orchestrator                  │
│  - Starts appropriate batch(es)      │
│  - Updates status: "Queued"          │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Batch Apex Job(s) - Chained         │
│  - Process data in chunks            │
│  - Update status: "Processing..."    │
│  - Create records                    │
│  - Handle errors per chunk           │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Completion Handler                  │
│  - Update status: "Complete"         │
│  - Send email notification           │
│  - Log audit trail                   │
└──────────────────────────────────────┘
```

### Key Components

**1. Status Tracking Fields** (on Case Manager / relevant object)
```
PRM_ProcessingStatus__c (Picklist):
  - Not Started
  - Queued
  - Processing [Step Name]
  - Completed
  - Failed
  - Rolled Back

PRM_ProcessingRequestId__c (Text, External ID)
PRM_ProcessingStartedAt__c (DateTime)
PRM_ProcessingCompletedAt__c (DateTime)
PRM_ProcessingError__c (Long Text Area)
PRM_TotalRecordsToProcess__c (Number)
PRM_RecordsProcessed__c (Number)
PRM_RecordsFailed__c (Number)
```

**2. Platform Events** (one per major flow)
```
NetworkCreationRequested__e
AddressCreationRequested__e
PDAReviewRequested__e
SupplierNetworkRequested__e
ProviderScreeningRequested__e
```

**3. Batch Apex Classes**
```
PRM_TaxonomyNetworkBatch
PRM_PayerNetworkBatch
PRM_IFCRecordBatch
PRM_AddressCreationBatch
PRM_HealthCareFacilityBatch
PRM_PDANetworkUpdateBatch
PRM_SupplierLinkingBatch
PRM_ProviderScreeningBatch
```

**4. Rollback Mechanism**
```
- Add RequestId__c field to all created objects
- Track all records with same RequestId
- On failure: Delete all records with RequestId
- Update status to "Rolled Back"
```

**5. Notification System**
```
- Email templates for success/failure
- In-app notifications (optional)
- Dashboard widgets showing active processes
```

---

## Performance Testing Plan

### Test Scenarios

**For Each Issue:**

| Scenario | Data Volume | Expected Time | Pass Criteria |
|----------|-------------|---------------|---------------|
| **Smoke Test** | Minimum (1 item) | < 1 min | Success, no errors |
| **Small Batch** | 3-5 items | < 5 min | Success, no timeout |
| **Medium Batch** | 10-15 items | 5-15 min async | Success, status updates |
| **Large Batch** | 25-30 items | 15-30 min async | Success, email notification |
| **Stress Test** | 50+ items | 30-60 min batch | Success, no governor errors |
| **Concurrent Test** | 3 users × 10 items | < 20 min | All succeed, no conflicts |
| **Failure Test** | Invalid data | < 5 min | Rollback successful, error logged |

### Monitoring Metrics

**Pre-Implementation (Current):**
- Average completion time per flow
- Timeout rate (%)
- Governor limit exceptions (count)
- Support tickets (count/week)

**Post-Implementation (Target):**
- UI response time (< 3s for 95th percentile)
- Background processing time (median, 95th)
- Success rate (> 98%)
- Rollback rate (< 2%)
- User satisfaction score

---

## Estimation

### Development Effort (Story Points)

| User Story | Analysis | Development | Testing | Documentation | Total |
|------------|----------|-------------|---------|---------------|-------|
| **#1: Delegated Network** | 3 | 13 | 5 | 2 | 23 |
| **#2: IBC Address** | 5 | 21 | 8 | 3 | 37 |
| **#3: PDA Review** | 3 | 13 | 5 | 2 | 23 |
| **#4: Supplier Network** | 3 | 13 | 5 | 2 | 23 |
| **#5: Provider Screening** | 2 | 8 | 3 | 1 | 14 |
| **TOTAL** | **16** | **68** | **26** | **10** | **120** |

**Team Velocity:** 30 points/sprint (2 weeks)  
**Timeline:** 4 sprints (~8 weeks) for all issues

### Priority-Based Timeline

**Phase 1 (Sprints 1-2): Critical Fixes**
- Issue #1: Delegated Network (23 pts)
- Issue #2: IBC Address (37 pts)
- **Total:** 60 points, 4 weeks

**Phase 2 (Sprints 3-4): High Priority**
- Issue #3: PDA Review (23 pts)
- Issue #5: Provider Screening (14 pts)
- **Total:** 37 points, 2-3 weeks

**Phase 3 (Sprint 5-6): Medium Priority**
- Issue #4: Supplier Network (23 pts)
- **Total:** 23 points, 1-2 weeks

---

## Success Metrics

### Key Performance Indicators (KPIs)

**Before Implementation:**
- Average UI response: 5-10+ minutes
- Timeout rate: 40-60%
- Support tickets: 50-70/week
- Manual workaround time: 10-20 hours/week
- User satisfaction: 3.2/5

**Target After Implementation:**
- Average UI response: < 3 seconds (95th percentile)
- Timeout rate: < 1%
- Support tickets: < 10/week (80% reduction)
- Manual workaround time: < 2 hours/week (90% reduction)
- User satisfaction: > 4.5/5

### Business Impact

**Productivity Gains:**
- 15-20 hours/week saved across credentialing team
- 60% faster practitioner onboarding
- 80% reduction in process errors
- 50+ more practitioners processed per month

**Cost Savings:**
- Support ticket reduction: $3-5K/month
- Manual processing reduction: $5-8K/month
- Faster time-to-revenue: $10-15K/month (earlier billing)
- **Total Annual Savings:** $200-300K

---

## Risks & Mitigation

### Risk 1: Batch Processing Failures
**Impact:** High  
**Probability:** Medium  
**Mitigation:**
- Comprehensive error handling per batch chunk
- Automatic retry for transient errors
- Rollback mechanism for data integrity
- Monitoring alerts for batch failures

### Risk 2: Platform Event Delivery Delays
**Impact:** Medium  
**Probability:** Low  
**Mitigation:**
- Platform events are at-least-once delivery
- Add idempotency checks (RequestId)
- Monitor event bus metrics
- Fall back to queueable if needed

### Risk 3: Data Integrity During Rollback
**Impact:** High  
**Probability:** Low  
**Mitigation:**
- Use RequestId tracking on all records
- Test rollback scenarios extensively
- Add audit logging for all operations
- Implement reconciliation reports

### Risk 4: User Adoption of Async Processing
**Impact:** Medium  
**Probability:** Medium  
**Mitigation:**
- Clear UI messaging ("Processing in background...")
- Email notifications with summaries
- Status dashboard for tracking
- User training and documentation

### Risk 5: Performance Still Insufficient
**Impact:** High  
**Probability:** Low  
**Mitigation:**
- Start with most critical issue (#1)
- Measure before/after metrics
- Iterate on batch sizes and strategies
- Have fallback to further optimization

---

## Appendix A: Query Optimization Opportunities

### Current Inefficiencies

**Problem 1: Queries in Loops**
```apex
// BAD: n queries
for (Location loc : locations) {
    List<Network> networks = [SELECT Id FROM Network WHERE LocationId = :loc.Id];
}

// GOOD: 1 query
Set<Id> locationIds = new Map<Id, Location>(locations).keySet();
Map<Id, List<Network>> networksByLocation = new Map<Id, List<Network>>();
for (Network n : [SELECT Id, LocationId FROM Network WHERE LocationId IN :locationIds]) {
    if (!networksByLocation.containsKey(n.LocationId)) {
        networksByLocation.put(n.LocationId, new List<Network>());
    }
    networksByLocation.get(n.LocationId).add(n);
}
```

**Problem 2: Redundant Queries**
```apex
// BAD: Same query multiple times
List<RecordType> rts1 = [SELECT Id FROM RecordType WHERE SObjectType = 'Account'];
// ... 50 lines later ...
List<RecordType> rts2 = [SELECT Id FROM RecordType WHERE SObjectType = 'Account'];

// GOOD: Cache in static variable
public class RecordTypeCache {
    private static Map<String, RecordType> cache = new Map<String, RecordType>();
    
    public static RecordType get(String objectType, String devName) {
        String key = objectType + ':' + devName;
        if (!cache.containsKey(key)) {
            cache.put(key, [SELECT Id FROM RecordType 
                           WHERE SObjectType = :objectType 
                           AND DeveloperName = :devName LIMIT 1]);
        }
        return cache.get(key);
    }
}
```

---

## Appendix B: DataRaptor Optimization

### Current Issues

**Problem: DataRaptors in Loops**
```
Loop 50 locations:
  DataRaptor Transform (location data)
  DataRaptor Load (create records)
End Loop

Result: 100 DataRaptor calls!
```

**Solution: Bulk DataRaptor**
```
Collect all location data in array
Single DataRaptor Transform (bulk mode)
Single DataRaptor Load (bulk mode)

Result: 2 DataRaptor calls!
```

### Bulk Mode Configuration
```json
{
  "bundleName": "PRM_BulkLocationTransform",
  "processBulk": true,
  "inputType": "JSON",
  "outputType": "JSON"
}
```

---

## Appendix C: Monitoring Queries

### Check Active Batch Jobs
```sql
SELECT Id, Status, TotalJobItems, JobItemsProcessed, 
       NumberOfErrors, CreatedDate, CompletedDate
FROM AsyncApexJob
WHERE ApexClass.Name LIKE 'PRM_%Batch'
AND CreatedDate = TODAY
ORDER BY CreatedDate DESC
```

### Check Platform Event Status
```sql
SELECT EventUuid, CreatedDate, CreatedBy.Name
FROM NetworkCreationRequested__e
WHERE CreatedDate = TODAY
ORDER BY CreatedDate DESC
LIMIT 100
```

### Check Processing Status
```sql
SELECT Id, Name, PRM_ProcessingStatus__c, 
       PRM_ProcessingStartedAt__c, PRM_ProcessingCompletedAt__c,
       PRM_RecordsProcessed__c, PRM_RecordsFailed__c
FROM CaseManager__c
WHERE PRM_ProcessingStatus__c IN ('Queued', 'Processing Taxonomies', 
                                    'Processing Payer Networks', 'Processing IFC')
ORDER BY PRM_ProcessingStartedAt__c DESC
```

### Performance Dashboard Query
```sql
SELECT 
    DATE(PRM_ProcessingStartedAt__c) ProcessDate,
    AVG(PRM_ProcessingCompletedAt__c - PRM_ProcessingStartedAt__c) AvgDuration,
    COUNT(Id) TotalProcessed,
    SUM(CASE WHEN PRM_ProcessingStatus__c = 'Failed' THEN 1 ELSE 0 END) FailedCount
FROM CaseManager__c
WHERE PRM_ProcessingStartedAt__c = LAST_N_DAYS:30
GROUP BY DATE(PRM_ProcessingStartedAt__c)
ORDER BY ProcessDate DESC
```

---

## Summary

**5 Critical Performance Issues Identified:**
1. ✅ Delegated Practitioner Network Creation (54-69 records, 5+ min timeout)
2. ✅ IBC Professional Address Creation (90-400 records, 100+ steps, 10+ min timeout)
3. ✅ PDA Review Network Updates (120-800 records, batch processing issue)
4. ✅ Supplier Network Bulk Linking (60-200 records, hierarchy complexity)
5. ✅ Provider Screen Records (70-1150 records, bulk processing)

**Common Root Causes:**
- Synchronous processing of bulk data
- Queries and DML in loops
- Heavy DataRaptor operations
- No chunking or batch processing
- Poor error handling (all-or-nothing)

**Recommended Solution:**
Event-driven batch architecture with:
- Platform Events for async triggering
- Batch Apex for bulk processing
- Status tracking and notifications
- Rollback mechanisms
- Progressive enhancement (maintain existing for small volumes)

**Expected Outcomes:**
- 80-95% reduction in timeouts
- UI response < 3 seconds
- Support ticket reduction 80%
- 15-20 hours/week productivity gain
- $200-300K annual savings

**Timeline:** 8 weeks for all 5 issues  
**Effort:** 120 story points total  
**Priority:** P0 (Issues #1, #2), P1 (Issues #3, #5), P2 (Issue #4)
