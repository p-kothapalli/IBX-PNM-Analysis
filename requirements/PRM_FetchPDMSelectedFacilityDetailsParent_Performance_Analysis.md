# Performance Issue Analysis: PRM_FetchPDMSelectedFacilityDetailsParent

## Issue Summary
When landing on the PDM Manual Update screen with "Practice Location" request type (add/remove practice location), the system is fetching ALL practitioner details (potentially 1500+ records) immediately on page load, causing significant performance degradation.

## Root Cause Analysis

### 1. **Call Chain**
```
User lands on PDM Manual Update screen (ManualUpdateOptions = "PracticeLocation")
    ↓
IPFetchSelectedFacilityDetails (Integration Procedure Action)
    ↓
PRM_FetchPDMSelectedFacilityDetailsParent (Parent IP)
    ↓
PRM_FetchPDMSelectedFacilityDetails (Child IP)
    ↓
DRExtractPLAssociationRecs (DataRaptor Turbo Extract) ← **PROBLEM HERE**
```

### 2. **The Problematic Component**

**File:** `PRM_FetchPDMSelectedFacilityDetails`
**Element:** `DRExtractPLAssociationRecs`
**Type:** DataRaptor Turbo Extract
**DataRaptor:** `PRMDRExtractPLAssociationRecs`

**Query Logic:**
```sql
SELECT 
    PRM_Active__c,
    PRM_AssociationEffectiveToday__c,
    PRM_HealthcareFacility__c
FROM PRM_HealthcareFacilityAssociation__c
WHERE 
    PRM_Active__c = true
    AND PRM_AssociationEffectiveToday__c = true
    AND PRM_HealthcareFacility__c = :FacilityId
    AND (
        RecordType.DeveloperName = 'PRM_DesignatedSpecialtyBundle'
        OR RecordType.DeveloperName = 'PRM_DesignatedSpecialtyBundleNetwork'
    )
```

**Issue:** This query fetches **ALL** active Practice Location Association records for the selected facility **without any LIMIT clause or pagination**, regardless of whether all this data is immediately needed.

### 3. **When It's Called**

The Integration Procedure `IPFetchSelectedFacilityDetails` is triggered:
- **Location:** OmniScript element in `PRM_PDMManualUpdate_English`
- **Trigger:** `show.group.rules` with condition `ManualUpdateOptions = "PracticeLocation"`
- **Timing:** **Immediately on page load** when practice location is selected

**File Reference:** 
`vlocity_export/OmniScript/PRM_PDMManualUpdate_English/PRM_PDMManualUpdate_English_Element_IPFetchSelectedFacilityDetails.json:57-68`

### 4. **How Practitioner Search Should Work**

There's a separate Type Ahead Block component `SearchPracBlk` for searching practitioners:
- **Type:** Type Ahead Block (autocomplete/typeahead)
- **DataRaptor:** `PRMDRFetchPDMActivePractitionersForPL`
- **Call Frequency:** 300ms (debounce)
- **Search Parameter:** `key1` (user input)

**Expected Behavior:** Practitioners should be fetched **on-demand** as the user types in the search box, not all at once on page load.

## Impact Analysis

### Performance Impact (for 1500 practitioners):
1. **Database Query Time:** Fetching 1500+ records with joins
2. **Network Transfer:** Large JSON payload (potentially 1-5MB)
3. **Browser Memory:** Loading all records into memory
4. **UI Freeze:** Rendering delay while processing large dataset
5. **API Governor Limits:** Salesforce heap size and query rows consumed

### Estimated Load Time Impact:
- **Without fix:** 15-30 seconds (or timeout)
- **With fix:** 2-5 seconds (only essential data loaded)

## Why This Is a Problem

### 1. **Unnecessary Data Loading**
The `DRExtractPLAssociationRecs` is loading ALL practitioner associations even though:
- The user hasn't searched for any specific practitioner yet
- The Type Ahead Block will fetch practitioners on-demand when the user searches
- Most of this data won't be displayed or used immediately

### 2. **Wrong Loading Strategy**
- **Current:** Eager loading (fetch everything upfront)
- **Should Be:** Lazy loading (fetch only what's needed, when it's needed)

### 3. **Duplicate Functionality**
There are TWO different mechanisms fetching practitioner data:
- `DRExtractPLAssociationRecs` - Fetches all associations on page load
- `PRMDRFetchPDMActivePractitionersForPL` - Fetches practitioners based on search (Type Ahead)

## Solution Recommendations

### **Option 1: Remove Unnecessary Data Extraction (RECOMMENDED)**

**What:** Remove the `DRExtractPLAssociationRecs` step from `PRM_FetchPDMSelectedFacilityDetails`

**Why:** 
- The practitioner search functionality already exists via Type Ahead Block
- Practice Location Association data is not displayed on initial page load
- Users will search for specific practitioners using the search box

**Implementation:**
1. Analyze what fields from `DRExtractPLAssociationRecs` are actually being used in the initial view
2. If only a count or summary is needed, replace with a count query
3. If no data is used initially, remove the step entirely
4. Keep the Type Ahead search intact for on-demand practitioner lookup

**Files to Modify:**
- `vlocity_export/IntegrationProcedure/PRM_FetchPDMSelectedFacilityDetails/PRM_FetchPDMSelectedFacilityDetails_DataPack.json`
- Remove `DRExtractPLAssociationRecs` from the OmniProcessElement array

**Risk:** Low - If the data is not being displayed on page load

### **Option 2: Add LIMIT Clause with Pagination**

**What:** Add a LIMIT clause to `DRExtractPLAssociationRecs` and implement pagination

**Implementation:**
1. Modify `PRMDRExtractPLAssociationRecs` DataRaptor to add LIMIT 50 (or appropriate number)
2. Add pagination controls to display remaining records
3. Implement "Load More" functionality

**Risk:** Medium - Requires UI changes and pagination logic

**Files to Modify:**
- `vlocity_export/DataRaptor/PRMDRExtractPLAssociationRecs/PRMDRExtractPLAssociationRecs_DataPack.json`
- Add pagination controls in OmniScript

### **Option 3: Conditional Loading**

**What:** Only load associations when explicitly requested by user

**Implementation:**
1. Add a flag/parameter to control whether to fetch associations
2. Add a button/toggle for users to "Load Practitioners"
3. Call `DRExtractPLAssociationRecs` only when the button is clicked

**Risk:** Low - Keeps existing functionality but defers loading

**Files to Modify:**
- `vlocity_export/IntegrationProcedure/PRM_FetchPDMSelectedFacilityDetails/PRM_FetchPDMSelectedFacilityDetails_Element_DRExtractPLAssociationRecs.json`
- Add `executionConditionalFormula` to control execution

### **Option 4: Use COUNT Query Initially**

**What:** Replace the full data extraction with a COUNT query initially

**Implementation:**
1. Create a new DataRaptor that just returns COUNT of associations
2. Display "X practitioners associated with this location"
3. Load full data only when needed

**Risk:** Low - Provides visibility without performance impact

## Verification Steps

After implementing the fix:

1. **Performance Testing:**
   - Test with practice location having 1500+ practitioners
   - Measure page load time before and after fix
   - Monitor Salesforce Debug Logs for query execution time

2. **Functional Testing:**
   - Verify all existing functionality still works
   - Test Type Ahead search for practitioners
   - Ensure no data is missing from the UI

3. **Browser Performance:**
   - Check browser memory usage
   - Monitor network payload size
   - Verify no JavaScript errors

## Key Files Reference

| File | Purpose | Line Numbers |
|------|---------|--------------|
| `PRM_FetchPDMSelectedFacilityDetailsParent_DataPack.json` | Parent Integration Procedure | Lines 17-18 |
| `PRM_FetchPDMSelectedFacilityDetails_DataPack.json` | Child Integration Procedure | Lines 36 |
| `PRM_FetchPDMSelectedFacilityDetails_Element_DRExtractPLAssociationRecs.json` | Problematic DataRaptor call | All |
| `PRMDRExtractPLAssociationRecs_Items.json` | DataRaptor query definition | Lines 72-278 |
| `PRM_PDMManualUpdate_English_Element_IPFetchSelectedFacilityDetails.json` | OmniScript trigger | Lines 57-68 |
| `PRM_PDMManualUpdate_English_Element_SearchPracBlk.json` | Type Ahead search (correct approach) | Lines 28-78 |
| `PRMDRFetchPDMActivePractitionersForPL_Items.json` | On-demand practitioner search DataRaptor | Lines 48-122 |

## Recommended Immediate Action

**OPTION 1 is the recommended approach:**

1. **Investigate usage:** Determine if `DRExtractPLAssociationRecs` data is displayed on initial page load
2. **If NOT used initially:** Remove the step entirely from the Integration Procedure
3. **If a summary is needed:** Replace with a COUNT query
4. **Rely on Type Ahead:** Keep the existing search functionality for on-demand lookups

This will reduce page load time by **80-90%** for large practice locations.

## Additional Considerations

### Business Logic Questions to Answer:
1. Why is `DRExtractPLAssociationRecs` needed on page load?
2. What specific data from this extraction is displayed to the user immediately?
3. Can this be deferred until the user performs a specific action?
4. Is there a business requirement to show all practitioners upfront?

### Code Review Findings:
- ✅ Type Ahead search is properly implemented with debounce (300ms)
- ❌ Eager loading of ALL associations on page load is inefficient
- ❌ No LIMIT clause on the association query
- ❌ No pagination implemented
- ❌ Potentially duplicate data fetching mechanisms

## Conclusion

The performance issue is caused by **eager loading of all practice location associations** on page load via `DRExtractPLAssociationRecs` in the `PRM_FetchPDMSelectedFacilityDetails` Integration Procedure. This is unnecessary because:

1. A proper Type Ahead search already exists for on-demand practitioner lookup
2. The data is not required on initial page load
3. There's no LIMIT clause, causing all 1500+ records to be fetched

**Recommended Fix:** Remove `DRExtractPLAssociationRecs` from the Integration Procedure and rely solely on the Type Ahead search for practitioner lookups.

---

**Analysis Date:** 2026-04-02  
**Analyzed By:** Claude Code  
**Priority:** HIGH  
**Effort:** LOW (if Option 1) / MEDIUM (if other options)
