# PRM UI Redesign — Case Manager & Guided Flows (SK Estimation)

**Business Ask:** Redesign UI across all objects and guided flows to improve user efficiency (fewer clicks).
Specifically: all objects related to the Case Manager should be **editable inline on the Case Manager
record itself**, rather than requiring users to navigate into related lists and drill down further.

**Business Value:**
- Improves business adoption of the system
- Allows processors to manage the full lifecycle of a case without leaving the Case Manager record
- Reduces turnaround time: fewer navigations = faster case processing
- Provider-level information accessible in fewer clicks

**Scope:**
- `IndividualApplication` (Case Manager) record page — primary focus
- `PRM_CaseDataManager__c` record page
- `PRM_PractitionerRecordPage`, `PRM_HealthcareFacilityRecordPage` (secondary)
- Guided flows (PDM Manual Change, Practitioner Creation) UX improvements

---

## Executive Summary

| | Baseline | AI + Senior Dev |
|---|---|---|
| **Total effort** | ~34 developer-days | **~20 developer-days** |
| **Calendar time (2 senior devs)** | ~3–4 sprints (6–8 weeks) | **2.5–3 sprints (5–6 weeks)** |
| **Risk level** | **Medium-High** | **Medium-High** |
| **Foundation already built** | Yes — significant head start (see Section 1) | Yes |

> **Key finding:** The read-only foundation for this feature already exists in the codebase
> (`prmCaseManagerRelatedList`, `prmNewRelatedList`, `PRM_CaseManagerAssociation__c`,
> `PRM_Relatedlistconfiguration__mdt`). However, the effort is **not** just wiring edit buttons.
>
> Every inline-editable object has active triggers that fire rollup chains, validation blocks,
> BCBSA sync events, and FDP records on every save. Termination actions (deactivate network,
> terminate practice location) cannot be a simple field flip — they must route through the
> correct batch class. Field-level validation errors from triggers must be surfaced in the LWC
> modal, not just as a generic toast. See **Section 7** for the full breakdown.
>
> **Phase 1–4 only (no guided flow UX):** ~16 days AI+senior, ~2–2.5 sprints, delivers the
> core inline edit experience. This is the recommended v1 scope.

---

## 1. What Already Exists (Critical Context)

### 1A. Existing LWC Components

| Component | What It Does | Gap |
|-----------|-------------|-----|
| `prmCaseManagerRelatedList` | Reads `PRM_CaseManagerAssociation__c` + `PRM_Relatedlistconfiguration__mdt`, renders related lists on Case Manager page | **Read-only. No inline edit. No add/remove.** |
| `prmNewRelatedList` | Generic datatable sub-component — renders columns, handles sort/search/pagination | **No inline edit rows. Navigation-only (hyperlinks to records).** |

### 1B. Existing Data Model (Already Supports the Feature)

**`PRM_CaseManagerAssociation__c`** — the junction object that ties a Case Manager to all related
records. Has 12 lookup fields covering every key object:

| Field | Object |
|-------|--------|
| `PRM_Account__c` | Account (Practitioner/Person Account) |
| `PRM_Address__c` | Address |
| `PRM_BusinessLicense__c` | BusinessLicense |
| `PRM_HealthcareFacility__c` | HealthcareFacility |
| `PRM_HealthcareFacilityAssociation__c` | PRM_HealthcareFacilityAssociation__c |
| `PRM_HealthcareFacilityNetwork__c` | HealthcareFacilityNetwork |
| `PRM_HealthcarePractitionerFacility__c` | HealthcarePractitionerFacility |
| `PRM_HealthcareProviderTaxonomy__c` | HealthcareProviderTaxonomy |
| `PRM_Identifier__c` | HealthcareProviderNpi |
| `PRM_ProgramParticipation__c` | ProgramParticipation |
| `PRM_ProviderFeature__c` | PRM_ProviderFeature__c |

**`PRM_Relatedlistconfiguration__mdt`** — Custom Metadata Type that drives which columns to show
per request type (`PRM_PDM_RequestType__c`). Already wired to the LWC. Currently covers:

- `Update Tax ID` → Identifiers list
- `Add/Remove Program Participation` → Program Participations list
- `Cross-Reference Practice Locations` → Practice Locations, Practitioners, Networks, Taxonomies, Info Codes, Addresses

**`PRM_CaseDataManager__c`** — Has 65 fields that store the "before" and "after" state of 20+
related objects per change request.

### 1C. Current State of `PRM_CaseManagerRecordPage`

The current record page has **30+ `lst:dynamicRelatedList` components** stacked on a single tab,
plus 2 `force:relatedListSingleContainer` components and the `prmCaseManagerRelatedList` LWC.
This is the root cause of the UX problem: users must scroll through dozens of related lists to find
the record they need, then click through to it to make changes.

---

## 2. Current UX Problem — Click Path Analysis

### Current Path to Edit a Network Record from a Case Manager

```
Case Manager record page
  → Scroll to "HealthcareFacilityNetwork" related list (30+ lists to scroll past)
  → Click "View All" to see all HFN records
  → Identify the correct HFN record
  → Click into the HFN record
  → Click "Edit"
  → Make change, Save
  → Navigate back to Case Manager

Total: 6–8 clicks + significant scroll
```

### Desired Path

```
Case Manager record page
  → Click "Networks" tab
  → Click inline edit icon on the row
  → Make change, Save (inline, no navigation)

Total: 3 clicks, no scroll, no navigation
```

---

## 3. Proposed Architecture — What to Build

### Core Design Principle

**Extend the existing `prmCaseManagerRelatedList` / `prmNewRelatedList` stack with:**
1. Inline edit rows (no navigation to the child record for common field changes)
2. Inline "New" quick-create form (modal or drawer) for adding related records
3. Row-level "Deactivate / Remove" action
4. A tabbed dashboard shell on the Case Manager page (replace 30+ related lists with one component)
5. A "Provider Summary" read/quick-edit card that surfaces practitioner data without navigating to the Account

---

## 4. Component Inventory — What to Build

### 4A. Shared Infrastructure

#### `PRM_InlineEditController` (new Apex class)

> Handles save/update operations for inline-edited records from the LWC.
> The existing `PRM_CaseManagerRelatedListController.fetchRelatedRecords` is `cacheable=true`
> (read-only). A separate imperative controller is needed for mutations.

```apex
public with sharing class PRM_InlineEditController {

    // Save a single record's field changes
    @AuraEnabled
    public static void saveRecord(String recordId, String objectApiName,
                                  Map<String, Object> fieldValues) {
        // Dynamically build SObject, apply FLS-safe update
    }

    // Insert a new related record (quick-create from Case Manager)
    @AuraEnabled
    public static String createRecord(String objectApiName,
                                      Map<String, Object> fieldValues,
                                      String caseManagerId) {
        // Insert + create PRM_CaseManagerAssociation__c link
    }

    // Deactivate a record (set PRM_IsActive__c = false, EffectiveTo = today)
    @AuraEnabled
    public static void deactivateRecord(String recordId, String objectApiName) {
        // Soft-delete pattern consistent with PRM conventions
    }

    // Fetch fields + editability for a given object + request type
    @AuraEnabled(cacheable=true)
    public static List<FieldDescriptor> getEditableFields(String objectApiName,
                                                          String requestType) {
        // Returns field list with isEditable flag per field
    }
}
```

**Why not `lightning/uiRecordApi updateRecord`?** The standard LDS wire can handle simple field
edits, but some objects (`HealthcareFacilityNetwork`, `HealthcareProviderTaxonomy`) require PRM
business logic on save (e.g. cascading IsActive, InfoCode recalculation). The Apex controller
allows that logic to be encapsulated.

#### Extend `PRM_Relatedlistconfiguration__mdt`

Add two new fields to the existing Custom Metadata Type:

| New Field | Type | Purpose |
|-----------|------|---------|
| `PRM_EditableFields__c` | Long Text | Comma-separated list of fields that are editable inline |
| `PRM_AllowInlineAdd__c` | Checkbox | Whether the "Add New" button appears for this related list |
| `PRM_DeactivateOnRemove__c` | Checkbox | Whether remove sets `PRM_IsActive__c = false` or hard-deletes |

This keeps the inline edit configuration **data-driven** and not hardcoded in the LWC.

---

### 4B. New LWC: `prmInlineEditableRelatedList`

> Extends `prmNewRelatedList` with inline row editing. No navigation required.
> Inline edit uses `lightning-record-edit-form` in a slide-out modal per row.

**Key capabilities added over `prmNewRelatedList`:**

| Capability | Implementation |
|-----------|----------------|
| Row-level "Edit" action | Row action button → opens `lightning-record-edit-form` modal with editable fields |
| Row-level "Deactivate" action | Row action → calls `PRM_InlineEditController.deactivateRecord`, refreshes list |
| "Add New" header button | Opens modal with blank `lightning-record-edit-form` → on save, also inserts `PRM_CaseManagerAssociation__c` link |
| Dirty-state indicator | Row highlights when unsaved local changes exist |
| Optimistic UI | Locally update row immediately; rollback on API error |

```html
<!-- Simplified structure of prmInlineEditableRelatedList -->
<template>
    <lightning-card title={relatedListTitleWithCount}>
        <div slot="actions">
            <template if:true={allowInlineAdd}>
                <lightning-button label="New" onclick={openNewRecordModal}></lightning-button>
            </template>
        </div>

        <lightning-datatable
            key-field="Id"
            data={dataToShow}
            columns={dataTableColumns}
            row-actions={rowActions}
            onrowaction={handleRowAction}
            onsort={handleSort}>
        </lightning-datatable>
    </lightning-card>

    <!-- Edit Modal -->
    <template if:true={showEditModal}>
        <c-prm-inline-edit-modal
            record-id={selectedRecordId}
            object-api-name={childObjectApiName}
            editable-fields={editableFields}
            onclose={closeModal}
            onsave={handleSave}>
        </c-prm-inline-edit-modal>
    </template>
</template>
```

---

### 4C. New LWC: `prmCaseManagerDashboard`

> Tabbed container that replaces the 30+ `lst:dynamicRelatedList` components on the
> Case Manager record page. Each tab groups related objects logically.

```
prmCaseManagerDashboard (tabbed shell)
  ├─ Tab: "Provider Info"
  │    ├─ prmProviderSummaryCard (key practitioner fields, quick-edit)
  │    └─ prmInlineEditableRelatedList → Identifiers (HealthcareProviderNpi)
  │    └─ prmInlineEditableRelatedList → Licenses (BusinessLicense)
  │
  ├─ Tab: "Practice Locations"
  │    └─ prmPracticeLocationSummaryTab
  │         ├─ Accordion per Practice Location
  │         │    ├─ prmInlineEditableRelatedList → Networks (HealthcareFacilityNetwork)
  │         │    ├─ prmInlineEditableRelatedList → Taxonomies (HealthcareProviderTaxonomy)
  │         │    └─ prmInlineEditableRelatedList → Info Codes (PRM_InfoCodeAssignment__c)
  │
  ├─ Tab: "Case Details"
  │    └─ prmInlineEditableRelatedList → Case Data Manager fields
  │    └─ prmInlineEditableRelatedList → Case Manager Associations
  │
  ├─ Tab: "Program & Features"
  │    └─ prmInlineEditableRelatedList → Program Participations
  │    └─ prmInlineEditableRelatedList → Provider Features
  │
  └─ Tab: "Exceptions"
       └─ prmInlineEditableRelatedList → Exception records from PRM_CaseDataManager__c
```

**Tab structure is driven by a new `PRM_CaseManagerDashboardConfig__mdt`** Custom Metadata Type —
so business/admins can reorder tabs and add new related lists without code changes.

---

### 4D. New LWC: `prmProviderSummaryCard`

> Surfaces key practitioner and practice location fields directly on the Case Manager page.
> Today users must navigate: Case Manager → Case → Account → to see practitioner NPI, specialty,
> board certifications, etc. This component removes that navigation.

**Fields surfaced (read with quick-edit on key fields):**

| Section | Fields | Source Object |
|---------|--------|---------------|
| Practitioner | Full Name, NPI, Specialty, DEA, Board Cert status | Account + HealthcareProvider |
| License | License Number, State, Expiration Date | BusinessLicense |
| CAQH | CAQH ID, Attestation Date, Status | HealthcareProviderNpi |
| Practice Location | Facility Name, Address, Phone | HealthcareFacility |
| Network Status | Active Networks count, Primary Network | HealthcareFacilityNetwork |

```apex
@AuraEnabled(cacheable=true)
public static ProviderSummaryData getProviderSummary(String caseManagerId) {
    // Joins: IndividualApplication → PRM_CaseDataManager__c → Account + HealthcareProvider
    // + HealthcareProviderNpi + BusinessLicense (primary) + HealthcareFacilityNetwork (active count)
}
```

---

### 4E. Record Page Updates (Flexipage)

**`PRM_CaseManagerRecordPage`** — Major redesign:
- Remove all 30+ `lst:dynamicRelatedList` components from the detail tab
- Replace with single `prmCaseManagerDashboard` component
- Keep: `force:highlightsPanel`, `runtime_sales_pathassistant:pathAssistant`, `prmBatchRecordException`
- Keep right sidebar: Chatter feed + relevant quick links

**`PRM_CaseDataManagerRecordPage`** — Minor update:
- Add `prmProviderSummaryCard` to show the practitioner context at the top
- Existing `force:detailPanel` + `force:relatedListContainer` stays, but move to secondary tab

**`PRM_PractitionerRecordPage`** — Add:
- A "Open Case Managers" tab: lists all `IndividualApplication` records for this practitioner
- Each row links to the Case Manager and shows status, stage, created date

**`PRM_HealthcareFacilityRecordPage`** — Add:
- Inline-editable networks/taxonomies section (reuse `prmInlineEditableRelatedList`)

---

### 4F. Guided Flow UX Improvements (Lower Priority)

The guided flows (PDM Manual Change, Practitioner Creation) have more complex UX reduction
opportunities. **These are lower priority** vs the record page work and should be a separate SK
or Phase 2 within this SK.

| Flow | UX Issue | Proposed Fix | Effort |
|------|----------|-------------|--------|
| PDM Manual Change — all types | First screen asks user to pick change type; requires knowing the internal type names | Replace with user-friendly tile selection screen (LWC override of first OmniScript step) | 2 days |
| Practitioner Creation | NPI lookup screen: no auto-fill from CAQH after NPI is entered, forcing manual re-entry | CAQH pre-fill LWC already exists (`prmCaqhAuthRequest`); ensure it pre-fills all available fields | 0.5 days |
| Practice Location PDM | Network selection requires knowing payer network IDs | Add typeahead search with network name → ID resolution | 1 day |
| All flows — confirmation screen | Generic "Submission received" message | Replace with contextual summary showing all records that will be created | 1 day |

---

## 5. Estimation Summary

### What's Already Built (Reduces Scope)

| Existing Asset | How it Reduces Effort |
|----------------|----------------------|
| `prmCaseManagerRelatedList` | Tab orchestration pattern is established; reuse controller query logic |
| `prmNewRelatedList` | Core datatable infrastructure reused in `prmInlineEditableRelatedList` — ~40% of that LWC is copy-forward |
| `PRM_CaseManagerAssociation__c` | Junction model already maps Case Manager → all related records; no new objects needed |
| `PRM_Relatedlistconfiguration__mdt` | Extending with 3 new fields vs building from scratch |
| `PRM_CaseManagerRelatedListController` | `getCaseManagerAssociations()` and `createMapOfRelatedList()` are reusable |

### Story Points / T-Shirt Size by Component

| Component | Baseline Days | AI + Senior Days | Size | Notes |
|-----------|--------------|-----------------|------|-------|
| **`PRM_InlineEditController`** (Apex, FLS-safe, deactivate + save + create) | 2 | 1 | M | AI generates boilerplate; senior adds PRM business logic (cascade IsActive etc.) |
| **Extend `PRM_Relatedlistconfiguration__mdt`** (3 new fields + records for all types) | 0.5 | 0.25 | XS | AI generates field XML; MDT records = admin config, minimal code |
| **`PRM_CaseManagerDashboardConfig__mdt`** (new config MDT for tab layout) | 0.5 | 0.25 | XS | AI generates from MDT pattern |
| **`prmInlineEditableRelatedList`** (extends `prmNewRelatedList` with edit/add/deactivate) | 3 | 1.5 | M | ~40% reused from existing; senior validates modal pattern + event handling |
| **`prmInlineEditModal`** (sub-component for edit/new forms) | 1.5 | 0.75 | S | `lightning-record-edit-form` wrapper — straightforward LWC pattern |
| **`prmProviderSummaryCard`** (practitioner fields surfaced, quick-edit) | 2 | 1 | M | Apex query join is the main complexity |
| **`prmPracticeLocationSummaryTab`** (accordion per location, nested related lists) | 2.5 | 1.25 | M | Hierarchical data pattern; AI generates accordion template |
| **`prmCaseManagerDashboard`** (tabbed shell, wires all sub-components) | 2 | 1 | M | Tab orchestration; relatively straightforward once sub-components exist |
| **`PRM_CaseManagerRecordPage` flexipage redesign** | 1 | 0.75 | S | Mostly drag-and-drop in App Builder; confirm mobile layout |
| **`PRM_CaseDataManagerRecordPage` update** | 0.5 | 0.25 | XS | Add `prmProviderSummaryCard`; minor layout change |
| **`PRM_PractitionerRecordPage` update** | 0.75 | 0.5 | S | Add "Open Case Managers" tab |
| **`PRM_HealthcareFacilityRecordPage` update** | 0.75 | 0.5 | S | Add inline networks/taxonomies section |
| **Guided Flow UX improvements** (4 items, Section 4F) | 4.5 | 3 | M | OmniStudio publishing is manual; AI helps with LWC overrides |
| **Unit tests** (all Apex + LWC Jest where applicable) | 3 | **0.75** | M | **AI biggest win — generates from existing test patterns in repo** |
| **Integration/E2E testing** (sandbox) | 3 | 2.5 | M | Manual — user interaction tests can't be skipped |
| **UAT + bug fixes** | 3 | 3 | M | **Human-only — business must validate the new inline edit UX** |
| **Deployment** | 0.5 | 0.5 | XS | Flexipage + LWC deploy; App Builder publish is manual |

### **Total Estimate**

| Phase | Baseline Days | AI + Senior Days | SP (1 SP = 0.5 day) |
|-------|--------------|-----------------|---------------------|
| **Phase 1: Shared Infrastructure** | 3 | **1.5** | **3 SP** |
| **Phase 2: Inline Edit Core** (`prmInlineEditableRelatedList` + modal) | 4.5 | **2.25** | **4.5 SP** |
| **Phase 3: Case Manager Dashboard** (all LWC sub-components) | 6.5 | **3.25** | **6.5 SP** |
| **Phase 4: Record Page Updates** (4 flexipages) | 3 | **2** | **4 SP** |
| **Phase 5: Guided Flow UX** | 4.5 | **3** | **6 SP** |
| **Phase 6: Testing + UAT** | 6 | **3.25** | **6.5 SP** |
| **Phase 7: Deployment** | 0.5 | **0.5** | **1 SP** |
| **Total** | **28 days** | **~16 days** | **~31 SP** |

> **Team assumption:** 2 senior developers with Cursor AI, Phase 2–4 run in parallel (1 dev on
> the LWC components, 1 dev on the Apex + MDT config), after Phase 1 infra is done.
>
> **Calendar estimate:**
> - Standard team: ~3–4 sprints (6–8 weeks)
> - **AI + senior team: ~2–2.5 sprints (4–5 weeks)**
>
> **Phase 5 (Guided Flow UX) is optional for v1.** If business wants record page wins first,
> phases 1–4 alone deliver the core "inline edit on Case Manager" ask and can be done in
> **~1.5 sprints (3 weeks)** with 2 senior devs + AI.

---

## 6. Sprint Breakdown Recommendation

### Sprint 1 (2 weeks) — Foundation + Inline Edit Core

| Task | Owner | Days |
|------|-------|------|
| Extend `PRM_Relatedlistconfiguration__mdt` (3 new fields) | Dev 1 | 0.25 |
| Create `PRM_CaseManagerDashboardConfig__mdt` | Dev 1 | 0.25 |
| Build `PRM_InlineEditController` (save + deactivate + create) | Dev 1 | 1 |
| Unit tests for `PRM_InlineEditController` (AI-generated) | Dev 1 | 0.25 |
| Build `prmInlineEditModal` sub-component | Dev 2 | 0.75 |
| Build `prmInlineEditableRelatedList` (extends `prmNewRelatedList`) | Dev 2 | 1.5 |
| Smoke test inline edit on a single related list (HFN) | Both | 0.5 |
| Build `prmProviderSummaryCard` + `PRM_ProviderSummaryController` | Dev 1 | 1.5 |
| MDT config records for all request types (editable field sets) | Dev 2 | 0.5 |
| **Sprint 1 Total** | | **~6.5 days** |

### Sprint 2 (2 weeks) — Dashboard + Record Pages + Guided Flow UX

| Task | Owner | Days |
|------|-------|------|
| Build `prmPracticeLocationSummaryTab` (nested accordion) | Dev 1 | 1.25 |
| Build `prmCaseManagerDashboard` (tabbed shell) | Dev 1 | 1 |
| `PRM_CaseManagerRecordPage` flexipage redesign | Dev 1 | 0.75 |
| `PRM_CaseDataManagerRecordPage` update | Dev 2 | 0.25 |
| `PRM_PractitionerRecordPage` + `PRM_HealthcareFacilityRecordPage` updates | Dev 2 | 1 |
| Guided flow UX — change type tile screen | Dev 2 | 2 |
| Guided flow UX — confirmation summary screen | Dev 2 | 1 |
| Integration E2E testing — all 4 record pages | Both | 2.5 |
| **Sprint 2 Total** | | **~9.75 days** |

### Sprint 3 (1 week buffer) — UAT + Polish + Deploy

| Task | Owner | Days |
|------|-------|------|
| UAT with business — Case Manager inline edit | Both | 3 |
| Bug fixes from UAT | Both | 1.5 |
| Final deployment + App Builder publish | Dev 1 | 0.5 |
| **Sprint 3 Total** | | **~5 days** |

---

## 7. Critical Technical Complexity — What the Original Estimate Missed

This section covers the four categories that make inline editing far more complex than a
standard CRUD LWC: trigger cascade chains, validation error surfacing, rollup/roll-down effects,
and termination scenarios. **These are not edge cases — they affect every object in scope.**

---

### 7A. Trigger Cascade Chains (Rollups + Roll-Downs)

Every object that a user can inline-edit has an active trigger. When `PRM_InlineEditController`
calls `update record`, those triggers fire — including multi-level cascade chains. Key ones found:

#### `PRM_HealthcareFacilityNetworkTrigger` (fires on every HFN edit)

Editing a **single HFN field** (e.g. `IsActive`, `EffectiveTo`, `PRM_PractitionerRole__c`,
`PayerNetworkId`, `PRM_Taxonomy__c`) triggers ALL of the following helper chains:

| Helper Method | What It Does | Objects Written |
|--------------|-------------|----------------|
| `hfnRecordsEffectiveRangeRollup` | **Rolls up** effective date ranges; creates/updates Practice Location Taxonomy records based on role × taxonomy × network | `HealthcareFacilityNetwork` (PLTx type) — new records written |
| `assignPartCodeBasedOnAccType` | Updates participation code on the linked Account | `Account` |
| `updatePanelStatus` | Updates panel status on Account for the payer network | `Account` |
| `setPracRoleOnPLAndPPL` | Sets Practitioner Role on `HealthcarePractitionerFacility` + PPL | `HealthcarePractitionerFacility` |
| `stampEndDateOnPLTaxMemSelPLA` | Stamps end date on PLTax + Member Selectable PLA | `HealthcareFacilityNetwork` |
| `updateMemSelPCPOnInactivePLTax` | Cascades MemberSelectablePCP flag down to PLTax | `HealthcareFacilityNetwork` |
| `futureDatedProcessing` | Creates/updates `PRM_FutureDatedProcessing__c` if effective dates changed | `PRM_FutureDatedProcessing__c` |
| `updateGUID` | Updates GUID on Practice Location Number records | `HealthcareFacilityNetwork` |
| `updateCaseDataManager` | Writes change back to `PRM_CaseDataManager__c` | `PRM_CaseDataManager__c` |
| `createEventStagingRecord` | **Fires BCBSA sync platform event** | `PRM_BCBSARecordsSyncEvents__e` |
| `directoryNetworkExceptionAutomation` | Updates exception flags | `PRM_CaseDataManager__c` |

**Net effect:** Inline editing one HFN network status field triggers writes to 5+ distinct
objects in the same transaction.

#### `PRM_HealthcarePractitionerFacilityTrigger` (fires on every HCPF edit)

| Helper Method | What It Does | Objects Written |
|--------------|-------------|----------------|
| `updateActiveLocationsCount` | **Rollup** on Account: count of active practice locations | `Account` |
| `updateAccountPNC` | Updates PNC (Primary Network Count) flag on Account | `Account` |
| `updatePrimaryFlagonExistingPPL` | Manages primary flag — only one HCPF can be primary; changes cascade across all sibling records | `HealthcarePractitionerFacility` (multiple) |
| `futureDatedProcessing` | FDP record creation | `PRM_FutureDatedProcessing__c` |
| `processAffCareCatEffectiveDates` | Affiliated care category effective date management | `HealthcarePractitionerFacility` |

#### `PRM_HealthcareFacilityTrigger` (fires on HCF edits)

| Helper Method | What It Does |
|--------------|-------------|
| `restrictUserToModifyHCFName` | **Validation** — throws `addError()` if name field changes |
| `updatePracLocNetworks` | Cascades network updates from facility to linked HFN records |
| `createAlternateContactOnLocationAdd` | Auto-creates contact records on facility add |

#### `PRM_IndividualApplication` trigger (fires on Case Manager save)

The `PRM_IATriggerHandler.afterUpdate` fires `bcbsaRecordSyncService.initiateBCBSARecordSyncProcess()`
on **every** update to a Case Manager record — including any inline edit of the CM summary fields
in `prmProviderSummaryCard`.

---

### 7B. `PRM_TriggerContextControl` — The Bypass Flag

```apex
public static Boolean isBulkContext = false; // Default: NOT bulk

public static Boolean inBulkContext() { return isBulkContext; }
```

Every trigger starts with:
```apex
if (PRM_TriggerContextControl.inBulkContext()) return; // Skip ALL logic
```

**What this means for inline edit:**
- `isBulkContext` defaults to `false` — so ALL trigger logic fires on inline saves
- This is the **correct behavior for data integrity**, but it means every inline save
  carries the full overhead of the trigger chain
- **The inline edit controller must NOT set `enableBulkContext()`** — doing so would bypass
  validation, rollups, and BCBSA sync silently

**Implication for estimation:** Testing must verify trigger side effects for every object
inline-editable. A simple "save field → toast success" test is insufficient.

---

### 7C. Validation Error Surfacing

#### Source of Validation Errors

PRM validation in triggers uses two patterns:

| Pattern | Example | How it reaches the UI |
|---------|---------|----------------------|
| `Trigger.addError(msg)` on a field | `restrictUserToModifyHCFName()` on HCF `beforeUpdate` | Salesforce wraps this in a `DmlException`; the message is in `ex.getDmlMessage(0)` |
| `Trigger.addError(msg)` on the record | Various business rule checks | Same — `DmlException` caught in Apex, rethrown as `AuraHandledException` |
| `AuraHandledException` from Apex | Explicit throw in controller | Standard LWC error handling |

#### Current Gap

The proposed `PRM_InlineEditController.saveRecord()` returns `void` and the LWC shows
a generic toast on any exception. This needs to be more precise:

```apex
// Required: catch DmlException and return structured errors back to LWC
@AuraEnabled
public static SaveResult saveRecord(String recordId, String objectApiName,
                                    Map<String, Object> fieldValues) {
    try {
        // ... build and update SObject
    } catch (DmlException e) {
        // Parse field-level errors from the trigger's addError() calls
        List<FieldError> errors = new List<FieldError>();
        for (Integer i = 0; i < e.getNumDml(); i++) {
            errors.add(new FieldError(
                e.getDmlFieldNames(i),      // Which field caused the error
                e.getDmlMessage(i)           // The addError() message text
            ));
        }
        return new SaveResult(false, errors);
    }
    return new SaveResult(true, null);
}
```

The LWC must then map `FieldError.fieldNames` back to the input fields shown in the
modal and display them **inline on the field**, not just as a generic toast.

**This adds ~1.5 days of effort** not captured in the original estimate: structured error
return type + LWC field-level error display.

---

### 7D. Termination Scenarios — NOT a Simple Field Flip

The original estimation described the "Deactivate" row action as:
> `PRM_InlineEditController.deactivateRecord(recordId)` → sets `PRM_IsActive__c = false`

**This is incorrect for termination scenarios.** A simple `IsActive = false` update on
HFN/HCPF/HPT records misses the full termination cascade that the existing batch classes execute:

#### `PRM_TerminatePracticeLocationNRelations` (batch) does ALL of this:
1. Calls `PRM_CrossRefBatchHelper.terminateFacilityAndRelations()` — terminates:
   - All `HealthcareFacilityNetwork` records for the facility
   - All `HealthcareProviderTaxonomy` records
   - All `HealthcarePractitionerFacility` records (for all practitioners at that location)
   - Stamps `EffectiveTo` dates on each record
2. Updates `PRM_CaseDataManager__c` with termination details
3. On finish: calls `PRM_PDMManualUtility.processPDMManualCrossRefFinish(caseManagerId)`
4. Updates Case status to the appropriate stage

There are **9 termination batch classes** covering different scenarios:

| Batch | Scenario |
|-------|---------|
| `PRM_PracticeLocationTerminationBatch` | Terminate a single practice location |
| `PRM_PractitionerTerminationBatch` | Terminate a practitioner at a location |
| `PRM_FullPractitionerTerminationBatch` | Full practitioner termination (all locations) |
| `PRM_AccountTerminationBatch` | Account-level termination |
| `PRM_ManualUpdatePracLocTerminationBatch` | PDM-driven practice location termination |
| `PRM_ProvChangeTerminationBatch` | Provider change-driven termination |
| `PRM_RCATLocationTerminationBatch` | RCAT location termination |
| `PRM_RCATNetworkTerminationBatch` | RCAT network termination |
| `PRM_TerminatePracticeLocationNRelations` | Cross-reference termination batch |

#### Revised Design for the "Deactivate" Action

The LWC "Deactivate" row action **must not** directly set `IsActive = false`. Instead:

```
User clicks "Terminate" on an HFN/HCPF row
    │
    ▼
Show confirmation modal: "Select termination effective date"
    │
    ▼
LWC calls PRM_InlineTerminationController.initiateTermination(recordId, objectType, effectiveDate)
    │
    ▼
Controller determines correct batch class based on objectType:
  - HFN row → PRM_PractitionerTerminationBatch or PRM_ManualUpdatePracLocTerminationBatch
  - HCPF row → PRM_PractitionerTerminationBatch
  - Full facility → PRM_PracticeLocationTerminationBatch
    │
    ▼
Invoke Database.executeBatch(appropriateBatch, ...)
    │
    ▼
Return "Termination queued" status (async — same pattern as SK High Volume)
    │
    ▼
LWC polls PRM_AsyncJobRequest__c (or CDM status) for completion
```

**Important:** If the High Volume SK (async processing) is delivered first, this inline
termination should reuse the `PRM_AsyncJobRequest__c` + `PRM_AsyncJobQueued__e` infrastructure.
If not, a simplified synchronous termination path is acceptable for single-record terminations
(1 location, <20 child records) but will need the async path for large practitioners.

---

### 7E. Rollup Summary — What Must Be Verified After Every Inline Save

After any inline save, these rollup fields must be verified in testing to confirm trigger
cascade fired correctly:

| Changed Object | Field Edited | Rollup/Cascade Verified |
|---------------|-------------|------------------------|
| `HealthcareFacilityNetwork` | `IsActive` | Account `PRM_PartCode__c`, `PRM_PanelStatus__c`; HCPF `PRM_PractitionerRole__c` |
| `HealthcareFacilityNetwork` | `EffectiveTo` | `PRM_FutureDatedProcessing__c` record created; PLTax `EffectiveTo` stamped |
| `HealthcareFacilityNetwork` | `PRM_PractitionerRole__c` | `hfnRecordsEffectiveRangeRollup` fires; may create/update PLTx HFN records |
| `HealthcarePractitionerFacility` | `IsActive` or `PRM_IsPrimary__c` | Account `PRM_ActiveLocationsCount__c`; sibling HCPF primary flag cleared |
| `HealthcareFacility` | `Name` | Trigger validation error — should be blocked in UI, not just Apex |
| `IndividualApplication` (CM) | Any field | BCBSA sync event fires — verify no unintended sync |

---

### 7F. Revised Component Design for `PRM_InlineEditController`

Given the above, the original single-method controller must be split:

```apex
public with sharing class PRM_InlineEditController {

    // 1. Simple field edits — triggers fire naturally, cascade handles rollups
    @AuraEnabled
    public static SaveResult saveFieldEdit(String recordId, String objectApiName,
                                           Map<String, Object> fieldValues) { ... }

    // 2. Structured error return (field-level, not generic toast)
    public class SaveResult {
        @AuraEnabled public Boolean success;
        @AuraEnabled public List<FieldError> errors;
    }

    public class FieldError {
        @AuraEnabled public List<String> fieldNames;
        @AuraEnabled public String message;
    }

    // 3. Termination — routes to correct batch based on object type + context
    @AuraEnabled
    public static String initiateTermination(String recordId, String objectApiName,
                                             Date effectiveDate, String caseManagerId) { ... }

    // 4. New record creation — also inserts PRM_CaseManagerAssociation__c link
    @AuraEnabled
    public static SaveResult createLinkedRecord(String objectApiName,
                                                Map<String, Object> fieldValues,
                                                String caseManagerId) { ... }

    // 5. Editable field descriptor — which fields are safe to edit inline vs require full flow
    @AuraEnabled(cacheable=true)
    public static List<FieldDescriptor> getEditableFields(String objectApiName,
                                                          String requestType) { ... }
}
```

---

### 7G. Fields That Must NOT Be Editable Inline

Some fields look editable but require the full OmniScript guided flow to be changed safely,
because their changes cascade to downstream objects that the inline editor cannot manage:

| Field | Object | Why Not Inline-Editable |
|-------|--------|------------------------|
| `Name` | `HealthcareFacility` | `restrictUserToModifyHCFName()` trigger blocks it; requires `PRM_PDMPracticeNameChange` flow |
| `PRM_Taxonomy__c` | `HealthcareFacilityNetwork` | Change triggers `hfnRecordsEffectiveRangeRollup` — may create/delete PLTx records; requires guided taxonomy flow |
| `PayerNetworkId` | `HealthcareFacilityNetwork` | Network change requires HFN clone + deactivate of old record, not field edit |
| `EffectiveFrom` (past date) | Any | Retroactive effective date changes require FDP; `PRM_FutureDatedProcessingBatchHandler` must process |
| `Status` → "Terminated" | `IndividualApplication` | Must invoke full termination batch chain |
| `IsActive` → `false` | `HealthcareFacility` | Must invoke `PRM_PracticeLocationTerminationBatch`, not direct update |

**These fields must be suppressed from the inline edit modal** (or shown read-only with a
link to "Open Guided Flow" instead). This is driven by `PRM_Relatedlistconfiguration__mdt`
`PRM_EditableFields__c` — only safe fields are listed there.

---

### 7H. Revised Effort for These Categories

| Category | Original Estimate | Revised Estimate | Delta |
|----------|------------------|-----------------|-------|
| `PRM_InlineEditController` | 1 day (AI + senior) | **2.5 days** | +1.5 |
| `prmInlineEditableRelatedList` | 1.5 days | **2.5 days** | +1 (field-level error display + termination modal) |
| `prmInlineEditModal` | 0.75 days | **1.25 days** | +0.5 (field suppression logic, safe vs unsafe fields) |
| Testing — trigger cascade verification | (not included) | **+2 days** | +2 |
| Termination routing logic | (not included) | **+1.5 days** | +1.5 |
| **Total delta** | | | **+6.5 days baseline / +4 days AI+senior** |

**Revised AI + Senior total: ~20 days (up from ~16 days)**
**Revised calendar: ~2.5–3 sprints with 2 senior devs (up from 2–2.5 sprints)**

---

## 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **`lightning-record-edit-form` doesn't support all PRM custom field types** (e.g. lookup with filter logic) | Medium | Medium | Fall back to navigation for complex fields; suppress unsafe fields via `PRM_EditableFields__c` MDT config |
| **FLS / Sharing violations on inline save** (some objects use `with sharing`) | Medium | High | `PRM_InlineEditController` must perform FLS check before DML; use `Schema.describeSObjectType` |
| **HFN trigger cascade fires on inline save** — may create unexpected PLTx records or update Account fields unexpectedly | **High** | **High** | `PRM_TriggerContextControl.inBulkContext()` is `false` by default — all trigger logic fires. Do NOT bypass it. Verify cascade in E2E tests on every editable HFN field. |
| **Trigger `addError()` messages not surfaced to LWC user** | **High** | High | Controller must catch `DmlException`, parse `getDmlMessage(i)` per field, return `SaveResult` with field-level errors (see Section 7C) |
| **"Deactivate" action routes to wrong termination batch** | **High** | **Critical** | There are 9 termination batch classes for different scenarios. `PRM_InlineTerminationController` must determine the correct batch from object type + context. Confirmed with team which batch applies to each inline scenario. |
| **Fields that are unsafe to edit inline are shown as editable** (e.g. HCF Name, Taxonomy, PayerNetworkId) | High | High | `PRM_Relatedlistconfiguration__mdt.PRM_EditableFields__c` must explicitly allowlist safe fields only; all others shown read-only with "Open Guided Flow" link |
| **BCBSA sync fires on every CM inline save** (`PRM_IATriggerHandler.afterUpdate`) | Confirmed | Medium | Confirm with integration team that single-field updates to CM are safe to sync; add `PRM_TriggerBypassPermission` on the inline edit service user if needed |
| **`PRM_CaseManagerRelatedListController.fetchCaseManagerAssociatedRecords` is `cacheable=true`** — mutations won't auto-refresh | Confirmed | Medium | After save, call `refreshApex` or fire `lightning/refresh` event |
| **30+ related list removal from `PRM_CaseManagerRecordPage`** breaks existing bookmarks/deep links | Low | Low | Deep links to the record page still work; only tab layout changes |
| **MDT config records must be created for all PDM request types** | High | Medium | At least 10 distinct request types need editable field MDT records — get approved in pre-sprint planning |
| **UAT: Business may want more fields editable than initially scoped** | High | Medium | Scope creep risk; confirm field-by-field edit list with business in Sprint 0 |
| **Guided flow UX changes require OmniStudio republish** | Confirmed | Low | Keep as separate changeset from LWC work |

---

## 8. AI Productivity Model

| Work Category | AI Acceleration | Reason |
|---------------|----------------|--------|
| LWC template generation (HTML/CSS) | **3×** | Tab shells, accordion patterns, modal wrappers are boilerplate; AI generates clean SLDS-compliant HTML |
| Apex controller (SOQL + DML) | **2.5×** | Pattern is established; AI generates from existing `PRM_CaseManagerRelatedListController` as reference |
| MDT field XML | **4×** | Pure boilerplate; AI generates all 6 XML files in one pass |
| LWC Jest unit tests | **3×** | AI generates from component signatures; senior reviews assertion logic |
| Flexipage XML | **1.5×** | Mostly App Builder (GUI); XML export/import for bulk changes |
| Guided flow LWC overrides | **2×** | Existing LWC override patterns in repo (`prmTextElemOverrideGeneric`) serve as templates |
| UAT | **1×** | Human-only |

> **Key non-compressible constraint:** Business must confirm the exact **field-by-field edit list**
> for each request type before `PRM_Relatedlistconfiguration__mdt` records can be populated.
> If this sign-off is delayed, it blocks MDT config and delays Sprint 2 record page work.
> **Get this approved in Sprint 0/pre-sprint planning, not during Sprint 1.**

---

## 9. Definition of Done

- [ ] Case Manager record page has a single tabbed `prmCaseManagerDashboard` (no standalone related lists)
- [ ] Related records are editable inline (edit modal opens without navigating to the child record)
- [ ] "New" button creates a record AND inserts `PRM_CaseManagerAssociation__c` link
- [ ] **"Terminate" row action routes to correct batch class** (not a direct `IsActive = false`)
- [ ] **Trigger cascade verified**: editing HFN `IsActive` → Account `PRM_PartCode__c` + `PRM_PanelStatus__c` + HCPF `PRM_PractitionerRole__c` all update correctly
- [ ] **Trigger cascade verified**: editing HCPF `IsActive` → Account `PRM_ActiveLocationsCount__c` updates correctly
- [ ] **Field-level validation errors from triggers display inline** in the edit modal (not generic toast)
- [ ] `HCF.Name` edit is blocked in UI (shown read-only; trigger validation not relied upon as the only guard)
- [ ] Unsafe fields (`PRM_Taxonomy__c`, `PayerNetworkId`, retroactive `EffectiveFrom`) are suppressed from inline edit
- [ ] `prmProviderSummaryCard` shows practitioner NPI, specialty, license status on Case Manager page
- [ ] `PRM_Relatedlistconfiguration__mdt` has records for all request types with `PRM_EditableFields__c` (allowlist only)
- [ ] All Apex classes have ≥ 80% unit test coverage
- [ ] BCBSA sync impact confirmed — single-record inline saves are safe to sync
- [ ] FLS / sharing verified for all objects
- [ ] Business UAT sign-off — specifically on termination UX (async vs sync result)
- [ ] No regression on existing guided flows (PDM Manual Change, Practitioner Creation, Termination)
- [ ] Mobile layout verified

---

## 10. Comparison: Current vs. Future State

| Metric | Current | Future (This SK) |
|--------|---------|-----------------|
| **Clicks to edit a network record** | 6–8 clicks + scroll | 3 clicks (tab → row → edit modal) |
| **Clicks to see practitioner NPI** | 4+ clicks (CM → Case → Account → HealthcareProvider) | 0 clicks (surfaced on CM page via `prmProviderSummaryCard`) |
| **Related lists on Case Manager page** | 30+ `lst:dynamicRelatedList` components | 1 tabbed `prmCaseManagerDashboard` with 5 tabs |
| **Configuration** | Hardcoded in IP/DR logic | Data-driven via `PRM_Relatedlistconfiguration__mdt` (already exists) + new `PRM_CaseManagerDashboardConfig__mdt` |
| **Inline add new record** | Navigate to child object → New → fill form → save → navigate back | Click "New" on related list → fill modal → save in place |
| **Error on save** | No feedback (silent DataRaptor failure) | Toast notification with field-level error |
| **Request types supported** | Varies by request type (MDT-driven, but editable MDT records are incomplete) | All request types have editable field sets in MDT |

---

*Document References:*
- *`PRM_HighVolume_Processing_SK_Estimation.md` — Async processing SK (related: async save from inline edit)*
- *`Provider_Data_Versioning_Estimation.md` — Versioning SK (related: effective-date fields on inline edit)*
- *`prmCaseManagerRelatedList.js` + `prmNewRelatedList.js` — Existing LWC foundation*
- *`PRM_CaseManagerRelatedListController.cls` — Existing Apex controller (read-only; mutations need new controller)*
- *`PRM_CaseManagerRecordPage.flexipage-meta.xml` — Current page with 30+ related lists*
- *`PRM_Relatedlistconfiguration__mdt` — Config MDT (extend, don't replace)*
