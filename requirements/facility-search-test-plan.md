# Facility Search - Comprehensive Test Plan

## Test Data
- **Account Name:** HMHMG Specialty Care
- **Tax ID:** 223376459
- **NPI:** 1215989249
- **Expected:** 815 practice locations

---

## Test 1: Initial Search Without Filters

### Steps:
1. Open the Address & Group Management modal
2. Click "Add New Location"
3. Enter:
   - Group NPI: `1215989249`
   - Group Tax ID: `223376459`
4. Select "HMHMG Specialty Care" from Group Name dropdown
5. Click "Search for Addresses"

### Expected Results:
- Status message: "Found 815 locations"
- Datatable shows first 50 locations
- All locations from HMHMG Specialty Care account
- Pagination shows "Page 1 of 17" (815 ÷ 50 = 16.3, rounds to 17)

### Debug Logs to Check:
**Browser Console (F12 → Console):**
```
loadFacilities() called with:
  zipFilter: []
```

**Salesforce Debug Logs:**
```
=== FILTER DEBUG START ===
zipFilter: []
hasAddressFilters: false
accountLocationIds count: 815
=== FILTER DEBUG END ===
```

---

## Test 2: Zip Code Filter - Exact Match

### Steps:
1. In "Filter Locations" panel, enter:
   - Zip Code: `07601`
2. Click "Apply Filters"

### Expected Results:
- Only locations with zip codes starting with `07601` should appear
- Should **NOT** show zip codes: `08050`, `08701`, `07753`, `08857`, `19195`
- Should show zip codes: `07601` (exact match)

### Debug Logs to Check:
**Browser Console:**
```
=== APPLYING FILTERS ===
Zip Filter: 07601

loadFacilities() called with:
  zipFilter: [07601]
```

**Salesforce Debug Logs:**
```
=== FILTER DEBUG START ===
zipFilter: [07601]
hasAddressFilters: true
Zip WHERE clause: PRM_Zip__c LIKE '07601%'
Address Query: SELECT ParentId, PRM_Zip__c FROM Address WHERE ParentId IN :accountLocationIds AND PRM_IsErrorRecord__c = false AND PRM_Zip__c LIKE '07601%'
Address query returned: X results
  Matched address zip: 07601 for LocationId: ...
Filtered locationIds count: X
=== FILTER DEBUG END ===
```

### If Test Fails:
Look for these issues in debug logs:
1. **zipFilter is empty/null** → JavaScript not capturing input value
2. **hasAddressFilters: false** → Filter detection logic broken
3. **Address query returned: 0** → No addresses match in that account
4. **Matched address zip: 08050** → Query returning wrong results (critical bug)

---

## Test 3: Multiple Filters Combined

### Steps:
1. Clear previous filters
2. Enter:
   - City: `Hackensack`
   - State: `NJ`
   - Zip Code: `07601`
3. Click "Apply Filters"

### Expected Results:
- Only locations matching ALL three criteria
- Very narrow result set (likely 1-3 locations)

### Debug Logs to Check:
**Salesforce Debug Logs:**
```
cityFilter: [Hackensack]
stateFilter: [NJ]
zipFilter: [07601]
Address Query: ... WHERE ... AND PRM_City__c LIKE '%Hackensack%' AND PRM_State__c = 'NJ' AND PRM_Zip__c LIKE '07601%'
```

---

## Test 4: Clear Filters

### Steps:
1. Click "Clear Filters"

### Expected Results:
- All filter inputs cleared
- Results return to showing all 815 locations
- Pagination resets to Page 1

### Debug Logs to Check:
```
Zip Filter: []  // Empty after clear
hasAddressFilters: false
accountLocationIds count: 815
```

---

## Test 5: Pagination with Filters

### Steps:
1. Apply zip filter: `07`
2. Click "Apply Filters"
3. Click "Next" to go to page 2

### Expected Results:
- Shows locations 51-100 that match the filter
- All locations still have zip codes starting with `07`
- Page counter shows "Page 2 of X"

---

## Test 6: Row Selection and Bulk Add

### Steps:
1. Filter by zip: `07601`
2. Select 2-3 locations by clicking checkboxes
3. Verify "Add Selected (3)" button updates count
4. Click "Add Selected (3)"

### Expected Results:
- Success toast: "Successfully added 3 location(s)"
- Existing Locations section updates with new additions
- Facility search reloads and shows selected facilities with "✓ Linked" status
- Cannot select already-linked facilities

---

## Test 7: Create New Location

### Steps:
1. Click "Create New Location"
2. Fill in all required fields:
   - Facility Name: `Test Location`
   - Address: `123 Test St`
   - City: `Hackensack`
   - State: `NJ`
   - Zip: `07601`
   - Phone: `(555) 555-5555`
3. Click "Create and Add Location"

### Expected Results:
- Success toast: "Location created and added successfully"
- New location appears in Existing Locations (Pending tab)
- Can edit/save/remove the pending location

---

## Known Issues to Investigate

### Issue 1: Zip Filter Showing Wrong Results
**Symptom:** Entering `07601` shows locations with zip `08050`, `08701`

**Possible Causes:**
1. **Frontend:** `facilityZipFilter` not being set correctly
2. **Backend:** `zipFilter` parameter is null/empty when query executes
3. **Query Bug:** LIKE clause not working as expected
4. **Data Issue:** Address records have incorrect zip codes

**How to Diagnose:**
Check debug logs in order:
1. Browser console → Is `zipFilter: [07601]` logged?
2. Apex debug → Is `zipFilter: [07601]` received?
3. Apex debug → What does the Address Query look like?
4. Apex debug → What zip codes are in "Matched address zip:" lines?

---

## How to Access Debug Logs

### Browser Console:
1. Press `F12` (Chrome/Edge) or `Cmd+Option+I` (Mac)
2. Go to "Console" tab
3. Perform test actions
4. Look for logs starting with "===" or specific filter messages

### Salesforce Debug Logs:
1. Setup → Debug Logs
2. Click "New" to create a user trace flag for your user
3. Set log level to "FINEST" for all categories
4. Perform test actions
5. Refresh Debug Logs page
6. Download and search for "=== FILTER DEBUG"

---

## Success Criteria

✅ **All tests pass if:**
1. Zip filter `07601` shows ONLY locations starting with `07601`
2. Clear filters returns all 815 locations
3. Multiple filters combine correctly (AND logic)
4. Pagination preserves filter state
5. Row selection works and count updates
6. Bulk add creates HealthcarePractitionerFacility records
7. Create new location works end-to-end

---

## Quick Test (30 seconds)

1. Search for HMHMG Specialty Care (NPI: 1215989249)
2. Enter zip: `07601` → Apply Filters
3. Check if results show ONLY zip codes starting with `07601`
4. If you see `08050` or `08701`, **filter is broken** → Check debug logs

---

## Reporting Issues

When reporting issues, include:
1. **Screenshot** of the results showing wrong zip codes
2. **Browser console logs** (copy/paste text)
3. **Salesforce debug logs** (search for "FILTER DEBUG" and copy that section)
4. **Exact steps** to reproduce

Example:
```
ISSUE: Zip filter not working
STEPS: Entered 07601, clicked Apply Filters
EXPECTED: Only 07601 zip codes
ACTUAL: Showing 08050, 08701, 07601
BROWSER LOG: [paste console output]
APEX LOG: [paste debug log section]
```
