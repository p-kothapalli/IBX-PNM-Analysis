# 🏗️ Architecture Reusability & Modularity Report
## Address & Group Manager → Credentialing Flows Tile-Based Redesign

**Date:** April 17, 2026  
**Author:** Senior Salesforce Technical Architect  
**Scope:** `prmAddressGroupManager`, `addressValidationModal`, `PRM_AddressManagementService`, `PRM_SmartAddressSearch`, `PRM_IPPreciselyAPICall`  
**Target Initiative:** Master Development Plan — Credentialing Flows LWC Redesign (Tile-Based Architecture)

---

## Executive Summary

This report evaluates the recently deployed **Address & Group Manager** (`prmAddressGroupManager`) components for reusability in the upcoming **Tile-Based LWC Redesign** of credentialing flows (Application Review, PSV, QC). The analysis covers 4 key areas: modularity, scalability, reusability inventory, and coupling risks.

**Key Findings:**
- The `addressValidationModal` LWC and `validateAddress()` Apex method are **fully plug-and-play** — zero modification needed for new tiles.
- `PRM_AddressManagementService.cls` is a **2,280-line monolith** spanning 6 domains — must be decomposed before Tile adoption.
- `bulkAddLocations()` and `createNewLocation()` are **not scalable** for the PSV tile's 100+ address requirement — async batch architecture required.
- `prmAddressGroupManager` (2,914 lines, 120+ tracked properties) is a **God Component** — not reusable, but shared utilities should be extracted.

**Estimated effort for Tile-readiness:** ~10–12 developer days for Priority 1 + 2 items.

---

## 1. Component Modularity & "Plug-and-Play" Readiness

### 1.1 `addressValidationModal` (LWC) — ✅ Excellent Decoupling

**Verdict: Ready for plug-and-play with zero modification.**

The modal is architecturally clean:

| Aspect | Assessment |
|--------|-----------|
| **@api inputs** | Generic: `validatedAddress`, `originalAddress`, `confidence`, `hasMatch` — no object-specific bindings |
| **Events out** | `addressselected` (detail: `selectedAddress`, `useValidated`, `standardized`, `lat/lng`) and `cancel` — pure data, no parent coupling |
| **Apex imports** | **None** — zero server dependencies |
| **Object references** | **None** — no `Case`, `Account`, or `HealthcareFacility` references |
| **isExposed** | `false` — child-only, correct for composition |
| **CSS** | Fully self-contained with `addr-*` namespace — no SLDS overrides that would bleed |

**Key Strength:** The modal is a pure "presentation + selection" component. It receives two address shapes, lets the user pick one, and emits the choice. Any parent tile (`prm_psvAddressVerification`, `prm_verificationModal`) can compose it directly by passing `@api` properties and listening for `addressselected`/`cancel`.

**One minor gap:** The `addressLine1/addressLine2/city/state/zip/zip4` shape is *implicitly* assumed but not formally documented via an `@api` typedef or JSDoc. For the Tile architecture, consider publishing a shared `AddressShape` constant or interface documentation.

**Integration pattern for new tiles:**
```html
<!-- Inside any new tile's template -->
<template if:true={showValidationModal}>
    <c-address-validation-modal
        validated-address={validatedAddress}
        original-address={originalAddress}
        confidence={validationConfidence}
        has-match={validationHasMatch}
        onaddressselected={handleAddressSelected}
        oncancel={handleValidationCancel}>
    </c-address-validation-modal>
</template>
```

---

### 1.2 `validateAddress()` (Apex) — ⚠️ Minor Coupling to OmniStudio IP

**Verdict: Reusable, but has one hidden dependency.**

**Call chain:**
```
validateAddress(Map<String, String> addressData)
    → omnistudio.IntegrationProcedureService.runIntegrationService('PRM_IPPreciselyAPICall', ...)
        → PRM_IPPreciselyAPICall Integration Procedure
            → PRMDRTPreciselyRequestData (DataRaptor Transform)
            → Precisely API HTTP Callout
            → RAPreciselyResponse (Response Action)
```

| Aspect | Assessment |
|--------|-----------|
| **Input** | `Map<String, String> addressData` — generic, no object binding |
| **Output** | `Map<String, Object>` with `success`, `validated`, `original`, `confidence`, `hasMatch` — generic |
| **Dependency** | Calls `PRM_IPPreciselyAPICall` Integration Procedure via `omnistudio.IntegrationProcedureService` |
| **Skip logic** | Reads `PRM_SkipPrecisely` custom metadata — graceful degradation ✅ |
| **Error handling** | Returns structured error on API failure — doesn't throw ✅ |

**Risk:** The `omnistudio.IntegrationProcedureService` import means the new `PSVReviewController` (or any new Apex class) can call `validateAddress()` as-is, BUT:
- The org must have the OmniStudio managed package deployed
- The `PRM_IPPreciselyAPICall` IP (6 procedures) must exist and be active

**Recommendation:** Extract `validateAddress()` and `parseValidatedAddress()` into a standalone `PRM_AddressValidationService` utility class. This isolates the Precisely integration from address CRUD operations and allows the PSV tiles to import only the validation concern.

---

### 1.3 `PRM_AddressManagementService.cls` — 🔴 Monolithic — Major Refactoring Required

**Verdict: Too monolithic for Tile architecture consumption.**

This class is **2,280 lines** with **17+ @AuraEnabled methods** spanning 6 distinct domains:

| Domain | Methods | Lines (approx.) |
|--------|---------|-----------------|
| **Soft Delete / Restore** | `markAddressAsError`, `restoreAddress` | ~120 |
| **Read Operations** | `getRecentAddresses`, `getExistingPractitionerLocations`, `getRecordContext` | ~200 |
| **Write Operations** | `updatePractitionerLocation`, `createNewLocation`, `bulkAddLocations` | ~550 |
| **Search** | `findAccountsByNpiAndTaxId`, `searchFacilitiesForGroup` | ~250 |
| **Picklist/Reference Data** | `getStateOptions`, `getCountyOptionsByState`, `getProviderTypeOptions`, `getTaxonomyOptions` | ~200 |
| **Address Validation** | `validateAddress`, `parseValidatedAddress` | ~220 |
| **Scenario Detection** | `detectLocationScenario` | ~80 |
| **Network/Taxonomy** | `addFacilityNetworks`, `addTaxonomiesToPractitionerFacility`, `getPractitionerTaxonomiesAndVendorType` | ~300 |

**Recommended decomposition for Tile architecture:**

```
PRM_AddressManagementService (current monolith — 2,280 lines)
    │
    ├── PRM_AddressValidationService        ← validateAddress, parseValidatedAddress
    │                                          (~220 lines, standalone)
    │
    ├── PRM_AddressPicklistService           ← getStateOptions, getCountyOptionsByState,
    │                                          getStateAbbreviation
    │                                          (~200 lines, cacheable reads)
    │
    ├── PRM_LocationCRUDService              ← createNewLocation, updatePractitionerLocation,
    │                                          detectLocationScenario
    │                                          (~600 lines, transactional writes)
    │
    ├── PRM_LocationBulkService              ← bulkAddLocations (+ future async batch)
    │                                          (~200 lines + new Batchable class)
    │
    ├── PRM_LocationQueryService             ← getExistingPractitionerLocations,
    │                                          getRecentAddresses, searchFacilitiesForGroup,
    │                                          findAccountsByNpiAndTaxId
    │                                          (~450 lines, read-only)
    │
    ├── PRM_SoftDeleteService                ← markAddressAsError, restoreAddress
    │                                          (~120 lines, audit-sensitive)
    │
    └── PRM_TaxonomyNetworkService           ← addTaxonomiesToPractitionerFacility,
                                               addFacilityNetworks, getProviderTypeOptions,
                                               getTaxonomyOptions, getPractitionerTaxonomiesAndVendorType
                                               (~300 lines)
```

This allows `PSVReviewController` to import only `PRM_AddressValidationService` and `PRM_LocationQueryService` without pulling in 2,280 lines of unrelated CRUD logic.

---

## 2. Large Volume & Async Processing Readiness

### 2.1 `bulkAddLocations()` — 🔴 Not Scalable for 100+ Addresses

**Current architecture (synchronous, lines 735–900):**

```
bulkAddLocations(facilityIds, practitionerId, caseManagerId, groupAccountId)
    → SOQL: query existing HPF records (1 query)
    → SOQL: query RecordType (1 query)
    → Loop: classify each facility as insert/update/skip
    → DML: insert new HPFs (1 DML statement)
    → DML: update existing HPFs (1 DML statement)
```

**Governor limit analysis for 100+ addresses:**

| Limit | Current Usage per Call | Risk at 100+ | Risk at 500+ |
|-------|----------------------|---------------|--------------|
| SOQL queries | 2 (existing records + record type) | ✅ Safe | ✅ Safe |
| DML statements | 2 (insert + update) | ✅ Safe | ✅ Safe |
| DML rows | 1:1 with facilityIds count | ✅ Safe | ⚠️ Approaching limit |
| CPU time | Linear with list size | ✅ Safe | ⚠️ Could timeout |
| Heap size | Holding all records in memory | ✅ Safe | ⚠️ Risk |

**Critical gap:** `bulkAddLocations` only creates `HealthcarePractitionerFacility` junction records. It does NOT handle the full 7-record creation chain. For the PSV tile's 100+ address scenario where *new* locations need creation, each address would trigger `createNewLocation()` which runs the full chain:

```
createNewLocation() = 7 sequential DML operations per address:
  1. INSERT Location
  2. INSERT Address
  3. SOQL  HealthcareProviderNpi (lookup)
  4. INSERT HealthcareFacility
  5. INSERT HealthcarePractitionerFacility
  6. INSERT HealthcareProviderTaxonomy (optional)
  7. INSERT HealthcareFacilityNetwork (optional)
```

**⚠️ At 100 new addresses = 500–700 DML operations — far exceeding the 150 DML statement limit.**

### 2.2 Required Architectural Changes for Async Pattern

**Recommendation: Implement a `PRM_LocationBatchProcessor` (Batchable + Platform Event hybrid):**

```
┌─────────────────────────────────────────────────┐
│  PSV Tile (LWC)                                 │
│    → Submits bulk request payload               │
│    → Receives Job ID immediately                │
│    → Subscribes to PRM_BulkJobStatus__e         │
│    → Updates progress bar in real-time          │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  PRM_LocationBulkService.submitBatch()  (Apex)  │
│    → Validates payload                          │
│    → Creates PRM_BulkJob__c tracking record     │
│    → Serializes addresses to staging records    │
│    → Enqueues PRM_LocationBatchProcessor        │
│    → Returns jobId immediately to LWC           │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  PRM_LocationBatchProcessor (Database.Batchable)│
│    → start():  query staged address payloads    │
│    → execute(): process batch of 10 addresses   │
│        → Bulkified 7-record chain               │
│        → Collection DML (not individual inserts)│
│        → Publish PRM_BulkJobStatus__e per batch │
│    → finish(): publish final completion event   │
│        → Update PRM_BulkJob__c with results     │
└─────────────────────────────────────────────────┘
```

**Key implementation changes needed:**

1. **Bulkify `createNewLocation()`** — Refactor to accept `List<CreateLocationRequest>` and perform all inserts via collection DML:
   ```apex
   // BEFORE (current — 7 individual inserts per address):
   insert loc;       // 1 DML
   insert addr;      // 1 DML
   insert facility;  // 1 DML
   insert hpf;       // 1 DML
   // ... Total: 7 DML × N addresses

   // AFTER (bulkified — 7 collection inserts total):
   insert allLocations;    // 1 DML for all locations
   insert allAddresses;    // 1 DML for all addresses
   insert allFacilities;   // 1 DML for all facilities
   insert allHPFs;         // 1 DML for all HPFs
   // ... Total: 7 DML regardless of N
   ```

2. **Add `Database.Batchable<SObject>`** implementation with `scope = 10` (70 DML rows per batch execution, well within governor limits)

3. **Platform Events** for real-time UI updates:
   ```apex
   // PRM_BulkJobStatus__e fields:
   //   JobId__c        (Text)
   //   Status__c       (Text: 'Processing', 'Completed', 'Failed')
   //   ProcessedCount__c (Number)
   //   TotalCount__c     (Number)
   //   ErrorCount__c     (Number)
   //   ErrorDetails__c   (Long Text)
   ```

4. **LWC subscription** via `lightning/empApi`:
   ```javascript
   import { subscribe } from 'lightning/empApi';
   // Subscribe to /event/PRM_BulkJobStatus__e
   // Filter by JobId__c matching the submitted job
   // Update progress bar and address list in real-time
   ```

### 2.3 Pagination Gaps

The current `searchFacilitiesForGroup()` implements basic `OFFSET/LIMIT` pagination (`pageSize = 50`), which is adequate. However:
- **Missing:** Total count query is done in the same transaction — for 10K+ facilities, this adds unnecessary SOQL time
- **Missing:** No cursor-based pagination — OFFSET becomes expensive at high page numbers
- **Recommendation:** Add `WHERE Id > :lastSeenId ORDER BY Id LIMIT :pageSize` cursor pattern for the PSV tile

---

## 3. Reusability Inventory Map

### 3.1 Ready As-Is (100% Plug-and-Play)

| Component | Type | Lines | Why It's Ready |
|-----------|------|-------|----------------|
| `addressValidationModal` | LWC | 140 (JS) + 115 (HTML) + 140 (CSS) | Zero Apex imports, generic `@api` contract, event-driven output. Any tile can compose it. |
| `validateAddress()` | Apex Method | ~100 | Stateless, `Map<String,String>` in / `Map<String,Object>` out. Any controller can call it. |
| `parseValidatedAddress()` | Apex Helper | ~50 | Pure function — parses Precisely response. Currently `private`; promote to `public` in new service class. |
| `PRM_IPPreciselyAPICall` | OmniStudio IP | 6 procedures | Fully decoupled external API integration. Called via `IntegrationProcedureService` — no code changes needed. |
| `getStateOptions()` | Apex Method | ~30 | `@AuraEnabled(cacheable=true)`, reads picklist metadata. Universal. |
| `getCountyOptionsByState()` | Apex Method | ~80 | `@AuraEnabled(cacheable=true)`, dependent picklist resolution. Universal. |

### 3.2 Requires Minor Refactoring (Decoupling Needed)

| Component | Type | Lines | What Needs Changing | Effort |
|-----------|------|-------|---------------------|--------|
| `PRM_SmartAddressSearch` | Apex Class | 80 | Hardcoded `maxResults = 200`, basic scoring (primary=100, other=50). Needs: configurable page size, SOSL support for fuzzy matching, `OFFSET` pagination for PSV 100+ requirement. | 2 days |
| `detectLocationScenario()` | Apex Method | ~80 | Uses `LIKE` matching on `addressLine1` — brittle for standardized vs. non-standardized addresses. Should use Precisely-normalized addresses for matching. Extract to `PRM_LocationMatchingService`. | 1 day |
| `getExistingPractitionerLocations()` | Apex Method | ~120 | Currently filters by `caseManagerId` via `AND (PRM_CaseManager__c = :caseManagerId OR PRM_CaseManager__c = null)`. PSV tile needs all locations regardless of case manager. Add overloaded method without CM filter. | 0.5 day |
| `getRecordContext()` | Apex Method | ~50 | Assumes `IndividualApplication` parent object. Add `objectApiName` parameter to support `Case`, `Verification__c`, etc. | 0.5 day |

### 3.3 Requires Major Refactoring / Rewrite (Too Tightly Coupled or Unscalable)

| Component | Type | Lines | Why Major Work Is Needed | Effort |
|-----------|------|-------|--------------------------|--------|
| `bulkAddLocations()` | Apex Method | ~170 | Synchronous, HPF-only creation. Needs async `Database.Batchable` pattern + full 7-record chain bulkification for 100+ addresses. Current pattern would hit 150 DML limit at ~20 new locations. | 3 days |
| `createNewLocation()` | Apex Method | ~220 | 7 sequential single-record DML inserts. Must be bulkified into collection DML for batch processing. Also tightly coupled — creates Location → Address → Facility → HPF → Taxonomy → Network in one transaction with no partial-success handling. | 3 days |
| `prmAddressGroupManager` (LWC) | LWC | 2,914 (JS) | 120+ `@track` properties, hardcoded to `IndividualApplication` record page, manages 10+ UI concerns (search, pagination, create, edit, validate, confirm, taxonomy, subtabs, datatables). The PSV/QC tiles will each need their own slim orchestrator. Extract shared utilities into `prmAddressUtils` module. | 2 days (utils extraction) |

---

## 4. Architectural Debt & Coupling Risks

### 4.1 Tight Coupling to Case / IndividualApplication

| Coupling Point | File & Location | Impact on Tile Architecture |
|----------------|-----------------|---------------------------|
| `@api recordId` assumes `IndividualApplication` | `prmAddressGroupManager.js` line 47 | PSV tile uses `Case` or custom `Verification__c` — cannot reuse parent LWC |
| `@api objectApiName` expected as `'IndividualApplication'` | `prmAddressGroupManager.js` line 48 | New tiles need different object context |
| `getRecordContext()` queries `IndividualApplication` → `Case` → `CaseManager` chain | `PRM_AddressManagementService.cls` | New tiles need a generic `getContext(recordId, objectType)` pattern |
| `caseManagerId` threaded through every method (15+ methods) | Throughout service class | PSV flow may use `assignedUserId` instead; needs parameter abstraction |
| README explicitly states "standalone component for Case record pages" | `prmAddressGroupManager/README.md` | Documentation coupling creates confusion |

### 4.2 Tight Coupling to OmniScript Data Shapes

| Coupling Point | File & Location | Impact |
|----------------|-----------------|--------|
| `PRM_PARProviderSearch` (existing Apex imported at line 20) | `prmAddressGroupManager.js` | This class was built for `PRM_PractitionerParticipationForm_English` OmniScript. Method signatures and return shapes assume OmniScript data node structure (`ParProviderSearchResultList`, etc.). |
| `getStateAbbreviation()` hardcoded to 4 states only | `PRM_AddressManagementService.cls` line ~1395 | Map contains only: `Delaware→DE`, `Maryland→MD`, `New Jersey→NJ`, `Pennsylvania→PA`. **Will fail silently for any state outside IBX's current 4-state coverage** (returns full name instead of abbreviation). |
| IP input shape `{ requestData: { AddressLine1, ... } }` | `validateAddress()` line 1988 | Coupled to `PRMDRTPreciselyRequestData` DataRaptor transform structure. If the IP is versioned or the DRT is refactored, this breaks. |
| `PRM_SkipPrecisely` custom metadata toggle | `validateAddress()` | Assumes specific custom metadata record exists — undocumented prerequisite |

### 4.3 UI State Management Debt (God Component Anti-Pattern)

The parent `prmAddressGroupManager.js` has **120+ `@track` properties** managing:

| Concern | Properties Count | Notes |
|---------|:---:|-------|
| Group search state | ~12 | NPI, TaxID, AccountId, filtering |
| Facility search + pagination | ~15 | Filters, results, pages, selected IDs |
| Create new location form | ~18 | All form fields |
| Edit location form | ~10 | Edit mode, selected location, validation |
| Address validation modal state | ~6 | Show/hide, validated/original data |
| Confirmation dialog state | ~6 | Title, message, resolve callback |
| Taxonomy / Provider type state | ~10 | Options, selections, auto-vendor-type |
| Subtab navigation state | ~8 | Show/hide, selected location, edit mode |
| Datatable state (active locations) | ~5 | Sort, search, page, page size |
| Datatable state (pending locations) | ~5 | Sort, search, page, page size |
| State/County picklist | ~3 | Options, disabled state |
| Misc UI flags | ~15 | Spinners, visibility toggles, search state |

**This is unsustainable for the Tile architecture.** Each tile should own only its specific concern (max 15–20 tracked properties).

### 4.4 Actionable Recommendations

#### Priority 1 — Extract Immediately (Blocks Tile Development)

| # | Action | Effort | Deliverable |
|---|--------|--------|-------------|
| 1 | **Create `PRM_AddressValidationService.cls`** — Move `validateAddress()`, `parseValidatedAddress()`, and the skip-Precisely logic. Expose as `public static` methods. Add JSDoc for address shape contract. | 1 day | Standalone class, unit tests |
| 2 | **Create `PRM_AddressPicklistService.cls`** — Move `getStateOptions()`, `getCountyOptionsByState()`, `getStateAbbreviation()`. Expand state mapping to all 50 states via Custom Metadata Type `PRM_StateMapping__mdt`. | 0.5 day | Standalone class, metadata records |
| 3 | **Create `c/prmAddressUtils` JS module** — Extract phone formatting (`replace(/\D/g, '')`), field validation (`validateLocationFields`), address shape normalization, and pagination helpers. Import into both existing parent and new tiles. | 0.5 day | Shared JS module |

#### Priority 2 — Required Before PSV Tile Go-Live

| # | Action | Effort | Deliverable |
|---|--------|--------|-------------|
| 4 | **Bulkify `createNewLocation()`** — Accept `List<CreateLocationRequest>`, use collection DML (`insert listOfLocations`) instead of individual inserts. Implement `Database.Savepoint` + rollback for transactional integrity. Return per-record success/failure results. | 3 days | Refactored method + tests |
| 5 | **Build `PRM_LocationBatchProcessor`** — `Database.Batchable<SObject>` with `scope = 10`. Platform Event (`PRM_BulkJobStatus__e`) for real-time progress. `PRM_BulkJob__c` custom object for job tracking. | 3 days | Batchable class + PE + custom object |
| 6 | **Decouple `getExistingPractitionerLocations()`** — Add overloaded method without `caseManagerId` filter. Add `OFFSET/LIMIT` pagination parameters. Support sorting options. | 1 day | Overloaded methods + tests |

#### Priority 3 — Technical Debt Cleanup

| # | Action | Effort | Deliverable |
|---|--------|--------|-------------|
| 7 | **Replace hardcoded state abbreviation map** with Custom Metadata Type (`PRM_StateMapping__mdt`) — extensible without code deployment, covers all 50 states + territories. | 0.5 day | CMDT records |
| 8 | **Add `@api objectApiName` routing** to `getRecordContext()` so it can resolve context from `Case`, `IndividualApplication`, or any new parent object polymorphically. | 1 day | Refactored method |
| 9 | **Deprecate `PRM_SmartAddressSearch`** — its own README says "placeholder - use existing PRM_PARProviderSearch." Consolidate search logic into `PRM_LocationQueryService` with configurable scoring and SOSL support. | 1 day | Consolidated class |
| 10 | **Document `AddressShape` contract** — Create a formal schema definition for the address data shape (`addressLine1`, `addressLine2`, `city`, `state`, `zip`, `zip4`, `county`, `latitude`, `longitude`) used across all components. Add as JSDoc typedef and Apex inner class. | 0.5 day | Documentation + types |

---

## 5. Summary Scorecard

| Component | Plug-and-Play | Scalability | Coupling Risk | Overall | Action |
|-----------|:---:|:---:|:---:|:---:|--------|
| `addressValidationModal` (LWC) | 🟢 | 🟢 | 🟢 | 🟢 | Ship as-is |
| `validateAddress()` (Apex) | 🟢 | 🟢 | 🟡 | 🟢 | Extract to own class |
| `PRM_IPPreciselyAPICall` (IP) | 🟢 | 🟢 | 🟢 | 🟢 | Ship as-is |
| State/County picklist methods | 🟢 | 🟢 | 🟡 | 🟢 | Extract + expand state map |
| `PRM_SmartAddressSearch` | 🟡 | 🟡 | 🟡 | 🟡 | Minor refactor |
| `detectLocationScenario` | 🟡 | 🟡 | 🟡 | 🟡 | Minor refactor |
| `getExistingPractitionerLocations` | 🟡 | 🟡 | 🟡 | 🟡 | Add overloads |
| `bulkAddLocations()` | 🔴 | 🔴 | 🟡 | 🔴 | Major refactor to async |
| `createNewLocation()` | 🔴 | 🔴 | 🟡 | 🔴 | Bulkify 7-record chain |
| `prmAddressGroupManager` (LWC) | 🔴 | 🔴 | 🔴 | 🔴 | Extract utils; tiles get new orchestrators |

---

## 6. Recommended Tile Architecture (Target State)

```
┌──────────────────────────────────────────────────────────────────┐
│  Credentialing Flow Shell (LWC)                                  │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────────┐ │
│  │ App Review  │ │ PSV Tile   │ │ QC Tile    │ │ Close Case   │ │
│  │ Tile        │ │            │ │            │ │ Tile         │ │
│  └──────┬─────┘ └──────┬─────┘ └──────┬─────┘ └──────┬───────┘ │
│         │              │              │               │          │
│  ┌──────┴──────────────┴──────────────┴───────────────┴───────┐ │
│  │               Shared Component Library                      │ │
│  │  ┌─────────────────────┐  ┌──────────────────────┐         │ │
│  │  │ addressValidation   │  │ prmAddressUtils       │         │ │
│  │  │ Modal (as-is)       │  │ (new shared module)   │         │ │
│  │  └─────────────────────┘  └──────────────────────┘         │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  Apex Service Layer (Decomposed)                                 │
│  ┌──────────────────┐  ┌─────────────────────┐                  │
│  │ PRM_AddressValid- │  │ PRM_AddressPicklist-│                  │
│  │ ationService      │  │ Service             │                  │
│  └──────────────────┘  └─────────────────────┘                  │
│  ┌──────────────────┐  ┌─────────────────────┐                  │
│  │ PRM_LocationCRUD- │  │ PRM_LocationBulk-   │                  │
│  │ Service           │  │ Service + Batchable │                  │
│  └──────────────────┘  └─────────────────────┘                  │
│  ┌──────────────────┐  ┌─────────────────────┐                  │
│  │ PRM_LocationQuery │  │ PRM_TaxonomyNetwork │                  │
│  │ Service           │  │ Service             │                  │
│  └──────────────────┘  └─────────────────────┘                  │
│  ┌──────────────────┐                                            │
│  │ PRM_SoftDelete-   │                                           │
│  │ Service           │                                           │
│  └──────────────────┘                                            │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  Integration Layer (No changes needed)                           │
│  ┌──────────────────────────────────────┐                        │
│  │ PRM_IPPreciselyAPICall (OmniStudio)  │                        │
│  └──────────────────────────────────────┘                        │
└──────────────────────────────────────────────────────────────────┘
```

---

## 7. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|:---:|:---:|------------|
| PSV tile hits governor limits with 100+ synchronous creates | **High** | **Critical** | Implement `PRM_LocationBatchProcessor` before PSV go-live |
| State abbreviation fails for states outside DE/MD/NJ/PA | **Medium** | **High** | Replace hardcoded map with `PRM_StateMapping__mdt` CMDT |
| OmniStudio IP version mismatch after org upgrade | **Low** | **High** | Pin IP version; add integration test for `validateAddress()` |
| New tiles accidentally import monolithic service class | **High** | **Medium** | Complete decomposition in Priority 1; deprecate old class |
| Address shape contract drift between components | **Medium** | **Medium** | Publish shared `AddressShape` typedef; enforce in code review |

---

*End of Architecture Reusability & Modularity Report*
