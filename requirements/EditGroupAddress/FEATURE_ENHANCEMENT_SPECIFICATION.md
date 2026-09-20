# Feature Enhancements: Subtab Navigation & DataTable for Active Locations

**Date:** April 13, 2026  
**Status:** Feature Enhancement Specification  
**Related Component:** `prmAddressGroupManager` LWC  
**Priority:** High (UX improvement for scale)

---

## 📋 Request 1: Replace Modal with Subtab Navigation

### **Problem Statement**

Currently, when users click "Update / Edit Address Details" button, a modal (`addressValidationModal`) appears. This approach has limitations:
- ❌ Modal overlays the entire form, blocking context
- ❌ Users cannot see the parent form or other fields while validating
- ❌ Modal switching feels disconnected from the workflow
- ❌ Not ideal for complex multi-step workflows

### **Proposed Solution**

Replace modal with an **inline subtab** that opens within the existing tab structure:

```
Current State:
┌─────────────────────────────────────┐
│ [Active] [Pending] [Add New]        │
│─────────────────────────────────────│
│ Existing content for current tab     │
└─────────────────────────────────────┘

Desired State:
┌─────────────────────────────────────┐
│ [Active] [Pending] [Add New]        │
│─────────────────────────────────────│
│                                     │
│ Sub-tabs within the current tab:    │
│ ┌─────────────────────────────────┐ │
│ │ [Edit Address] [Validate]       │ │
│ │ [Back to List]                  │ │
│ ├─────────────────────────────────┤ │
│ │ Address Validation Content      │ │
│ │ (side-by-side comparison)       │ │
│ └─────────────────────────────────┘ │
│                                     │
└─────────────────────────────────────┘
```

---

## 🎯 Detailed Prompt for Claude: Subtab Implementation

### **Prompt:**

```
You are implementing a UI enhancement for the prmAddressGroupManager LWC component.

CURRENT STATE:
- When users click an "Edit" button on an address, an addressValidationModal appears as a modal overlay
- The modal shows recommended vs. provided address side-by-side

DESIRED STATE:
- Replace the modal with an inline subtab approach
- When edit is clicked, show a new subtab in the current tab (e.g., "Edit Address")
- The subtab should display the address validation side-by-side comparison
- Users can navigate between the main list view and the edit view seamlessly
- A "Back" button returns to the main list

REQUIREMENTS:

1. COMPONENT STRUCTURE
   - Modify prmAddressGroupManager.html to include:
     * Main tabs (Active / Pending / Add New) - existing
     * Conditional subtab area within each main tab
     * Subtab navigation with "Back to List" link/button
   - Keep prmAddressGroupManager.js for state management
   - Remove direct addressValidationModal usage in favor of subtab content

2. STATE MANAGEMENT (JavaScript)
   Add tracked properties:
   - @track showEditSubtab = false;
   - @track selectedLocationForEdit = null;
   - @track currentEditMode = null; // 'edit' | 'validate' | 'view'
   - @track editAddressData = {};

3. METHODS TO CREATE/MODIFY
   a) handleEditLocation(locationId)
      - Set showEditSubtab = true
      - Store selectedLocationForEdit
      - Populate editAddressData from selected location
      - Switch currentEditMode to 'edit'

   b) handleValidateAddress()
      - Call validateAddress() Apex method
      - On success, show comparison in subtab
      - Switch currentEditMode to 'validate'
      - Display recommended vs provided side-by-side

   c) handleUseRecommendedAddress()
      - Accept the recommended address
      - Update editAddressData
      - Call updatePractitionerLocation()
      - Refresh location list
      - Show confirmation toast
      - Close subtab and return to list

   d) handleUseProvidedAddress()
      - Accept the user-provided address
      - Update editAddressData
      - Call updatePractitionerLocation()
      - Refresh location list
      - Show confirmation toast
      - Close subtab and return to list

   e) handleBackToList()
      - Set showEditSubtab = false
      - Clear selectedLocationForEdit
      - Reset editAddressData
      - Reset currentEditMode
      - Optionally show confirmation if unsaved changes

4. HTML STRUCTURE (Conditional)
   When NOT in subtab mode (showEditSubtab = false):
   - Show existing Active Locations table/list
   - Show "Edit" button for each location

   When IN subtab mode (showEditSubtab = true):
   - Hide the main list
   - Show subtab header:
     * Breadcrumb: "Active Locations > Edit Address"
     * "Back to List" button
   - Show edit form with editable fields:
     * Address Line 1/2
     * City
     * State (combobox)
     * County (combobox, dependent on state)
     * Zip
     * Phone
     * Phone Extension
     * Is Primary (checkbox)
     * Telehealth Only (checkbox)
   - Show "Validate Address" button
   - When validation runs, show side-by-side comparison:
     * Left: Recommended address (from Precisely, green)
     * Right: Provided address (user-entered, neutral)
     * Confidence badge
     * Geocoding indicator
     * Action buttons: "Use Recommended" | "Use Provided"

5. CSS UPDATES
   - Style for subtab header (breadcrumb style)
   - Subtle background for edit form
   - Smooth transition when entering/exiting subtab
   - Responsive layout for side-by-side comparison
   - Mobile-friendly (stack vertically on small screens)

6. USER EXPERIENCE
   - Preserve scrolling position when returning from subtab
   - Show unsaved changes warning if user tries to navigate away
   - Disable back button while processing (validation, update)
   - Show loading indicators during async operations
   - Success/error toasts for all operations
   - Keyboard support (Escape key to cancel)

7. ACCESSIBILITY
   - ARIA labels for subtab controls
   - Proper heading hierarchy
   - Form validation error messages
   - Screen reader announcements for subtab transitions
   - Focus management (focus subtab on open, focus list on close)

INTEGRATION POINTS:
- Replace all addressValidationModal dispatches with handleValidateAddress()
- Replace modal event listeners with direct method calls
- Preserve all Apex method calls (validateAddress, updatePractitionerLocation, etc.)

TESTING CONSIDERATIONS:
- Test edit flow with and without address validation
- Test navigation between list and subtab
- Test unsaved changes detection
- Test with different screen sizes
- Test keyboard navigation (Tab, Escape, Enter)
- Test async operation handling (loading states)

OUTPUT:
Provide:
1. Updated prmAddressGroupManager.html with subtab structure
2. Updated prmAddressGroupManager.js with new methods and state
3. CSS updates for subtab styling
4. Detailed implementation notes for any complex sections
5. Migration guide (how to transition from modal to subtab)
```

---

## 📋 Request 2: DataTable for Active Locations

### **Problem Statement**

Currently, active locations display as a simple list view. Issues:
- ❌ For 50+ locations, massive scrolling required
- ❌ No column sorting or filtering
- ❌ Poor visibility of key information
- ❌ No pagination
- ❌ Difficult to find/manage specific locations

### **Proposed Solutions**

**Option 1: Lightning DataTable (Recommended)**
```
┌───────────────────────────────────────────────────────────────────┐
│ Active Locations (47 records)                                     │
├───────────────────────────────────────────────────────────────────┤
│ Location Name | Address | City | State | Primary | Phone | Action│
├───────────────────────────────────────────────────────────────────┤
│ Main Office   | 123 M... | Phi... | PA | ☑ | 215-555-0001 | [Edit]│
│ Branch 1      | 456 B... | New... | NJ | ☐ | 201-555-0002 | [Edit]│
│ Branch 2      | 789 S... | Bal... | MD | ☐ | 410-555-0003 | [Edit]│
│                                    ... (pagination) ...            │
└───────────────────────────────────────────────────────────────────┘
```

**Option 2: Hybrid - Mini View + Expandable Details**
```
┌───────────────────────────────────────────────────────────────────┐
│ Active Locations (47 records)  [Search: ________] [Show 10 ▼]    │
├───────────────────────────────────────────────────────────────────┤
│ ► Main Office (PO Box 48025, Newark, NJ 07101) Primary [Edit] [×]│
│ ► Branch 1 (PO Box 1515, Elizabeth, NJ 07207) [Edit] [×]        │
│ ► Branch 2 (PO Box 827800, Philadelphia, PA 19182) [Edit] [×]   │
└───────────────────────────────────────────────────────────────────┘
```

**Option 3: Scrollable Card List with Quick Actions**
```
┌───────────────────────────────────────────────────────────────────┐
│ Active Locations (47 records)  [Filter ▼]  [Sort ▼]              │
├───────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────┐  │
│ │ MAIN OFFICE                          Primary    [Edit] [×]  │  │
│ │ PO Box 48025                                                │  │
│ │ Newark, NJ 07101                                           │  │
│ │ Phone: 7329238704                                          │  │
│ └─────────────────────────────────────────────────────────────┘  │
│ ┌─────────────────────────────────────────────────────────────┐  │
│ │ RWJ UNIVERSITY HOSPITAL - RAHWAY          [Edit] [×]        │  │
│ │ PO Box 1515                                                │  │
│ │ Elizabeth, NJ 07207                                        │  │
│ │ Phone: 2159999999                                          │  │
│ └─────────────────────────────────────────────────────────────┘  │
│                          [Load More...]                           │
└───────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Detailed Prompt for Claude: DataTable Implementation

### **Prompt:**

```
You are implementing a UI enhancement for displaying active locations in the prmAddressGroupManager LWC component.

CURRENT STATE:
- Active locations display as a simple list/card view
- Screenshot shows 3 locations
- Each location takes up significant vertical space
- No pagination, sorting, or filtering
- Scrolling would be problematic with 50+ locations

DESIRED STATE:
- Replace simple list with a data-driven table
- Support for 50+ locations without excessive scrolling
- Easy to scan and find specific locations
- Sorting and filtering capabilities
- Responsive design

APPROACH:
Use Lightning Data Table (lightning-datatable) - the native Salesforce Lightning component designed for tabular data.

REQUIREMENTS:

1. COLUMNS TO DISPLAY
   a) Location Name (sortable, searchable)
   b) Address (Address Line 1 + City/State)
      - Formatted as: "123 Main St, Philadelphia, PA"
   c) Zip Code (sortable)
   d) Primary Location (checkbox, visual indicator - ☑ or ☐)
   e) Telehealth Only (checkbox, visual indicator)
   f) Phone Number (sortable)
   g) Status (Badge: "Active")
   h) Actions (inline buttons: Edit, Remove)

2. LIGHTNING DATA TABLE CONFIGURATION
   Properties:
   - data={activeLocationsData} // Array of location records
   - columns={activeLocationsColumns} // Column definitions
   - key-field="locationId" // Unique identifier
   - onsort={handleSort} // Handle column sorting
   - onrowaction={handleRowAction} // Handle row actions (Edit/Remove)
   - hide-checkbox-column={true} // Don't need row selection
   - show-row-number-column={true} // Show row numbers (optional)
   - resize-column-disabled={false} // Allow column resizing

3. COLUMN DEFINITIONS (JavaScript)
   Define in connectedCallback() or static:
   
   Example structure:
   [
     {
       label: 'Location Name',
       fieldName: 'locationName',
       type: 'text',
       sortable: true,
       wrapText: true,
       cellAttributes: {
         alignment: 'left'
       }
     },
     {
       label: 'Address',
       fieldName: 'formattedAddress', // Computed field
       type: 'text',
       sortable: false,
       wrapText: true,
       initialWidth: 200
     },
     {
       label: 'Zip',
       fieldName: 'zip',
       type: 'text',
       sortable: true
     },
     {
       label: 'Primary',
       fieldName: 'isPrimary',
       type: 'boolean', // Renders as checkbox
       sortable: true,
       cellAttributes: {
         alignment: 'center'
       }
     },
     {
       label: 'Telehealth',
       fieldName: 'telehealthOnly',
       type: 'boolean',
       sortable: true,
       cellAttributes: {
         alignment: 'center'
       }
     },
     {
       label: 'Phone',
       fieldName: 'phone',
       type: 'phone',
       sortable: true
     },
     {
       label: 'Status',
       fieldName: 'status',
       type: 'text',
       cellAttributes: {
         class: { fieldName: 'statusClass' } // Dynamic CSS
       }
     },
     {
       type: 'action',
       typeAttributes: {
         rowActions: [
           { label: 'Edit', name: 'edit' },
           { label: 'Remove', name: 'remove' }
         ],
         menuAlignment: 'auto'
       }
     }
   ]

4. DATA TRANSFORMATION
   Transform activeLocations array to match table format:
   
   activeLocationsData = this.activeLocations.map((loc, index) => ({
     locationId: loc.Id,
     locationName: loc.Name,
     address1: loc.Address?.AddressLine1 || '',
     city: loc.Address?.City || '',
     state: loc.Address?.State || '',
     zip: loc.Address?.Zip || '',
     formattedAddress: `${loc.Address?.AddressLine1 || ''}, 
                        ${loc.Address?.City || ''}, 
                        ${loc.Address?.State || ''}`,
     isPrimary: loc.PRM_Primary__c === true,
     telehealthOnly: loc.PRM_TelehealthOnly__c === true,
     phone: loc.Address?.Phone || '',
     status: 'Active',
     statusClass: 'active-status' // For badge styling
   }));

5. METHODS TO CREATE
   a) getActiveLocationsColumns()
      - Returns column definitions array
      - Call in connectedCallback()
      - Store in @track activeLocationsColumns

   b) getFormattedActiveLocationsData()
      - Transforms activeLocations to data table format
      - Adds computed fields (formattedAddress, statusClass)
      - Returns array for data table
      - Call after loading activeLocations

   c) handleSort(event)
      - Extract sortedBy (column name) and sortDirection (asc/desc)
      - Sort activeLocationsData based on column
      - Update @track sortBy and sortDirection
      - Update activeLocationsData
      - Re-render data table

   d) handleRowAction(event)
      - Extract action.name ('edit' or 'remove')
      - Extract event.detail.row (selected location record)
      - Call appropriate handler:
        * handleEditLocation(locationId) for 'edit'
        * handleRemoveLocation(locationId) for 'remove'

   e) handleRemoveLocation(locationId)
      - Show confirmation dialog
      - Call Apex method to soft-delete
      - Refresh activeLocations
      - Update data table
      - Show success toast

6. SEARCH & FILTERING
   Add optional search box above table:
   <lightning-input
     label="Search Locations"
     type="search"
     placeholder="Search by name, address, phone..."
     onchange={handleSearch}
     value={searchTerm}>
   </lightning-input>

   Method: handleSearch(event)
   - Get search term
   - Filter activeLocationsData based on search
   - Update data table
   - Show "X results found"

7. PAGINATION
   Option A: Lightning Data Table built-in
   - Use infinite scroll (load more on scroll)
   - Show first 10, load more on demand
   
   Option B: Manual pagination
   - Add "Show 10 / 25 / 50" dropdown
   - Implement next/previous buttons
   - Track current page

8. SORTING & FILTERING
   Pre-built filters:
   - "All Locations" (default)
   - "Primary Locations Only"
   - "Telehealth Only"
   - "By State" (NJ / PA / DE / MD)

   Example:
   <lightning-button-group>
     <lightning-button label="All" onclick={handleFilterAll}></lightning-button>
     <lightning-button label="Primary" onclick={handleFilterPrimary}></lightning-button>
     <lightning-button label="Telehealth" onclick={handleFilterTelehealth}></lightning-button>
   </lightning-button-group>

9. RESPONSIVE DESIGN
   - On mobile: Hide non-essential columns (Status)
   - Show abbreviated address on mobile
   - Keep Action column visible
   - Stack Actions vertically on small screens

10. CSS FOR STATUS BADGE
    .active-status {
      background-color: #04844b;
      color: white;
      padding: 4px 8px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: bold;
      display: inline-block;
    }

    .primary-indicator {
      color: #0070d2;
      font-weight: bold;
    }

11. PERFORMANCE CONSIDERATIONS
    - For 50+ locations, consider virtual scrolling
    - Load data in batches (first 20, then on-demand)
    - Use @track for minimal re-renders
    - Cache transformed data
    - Only re-transform when data changes

12. ACCESSIBILITY
    - Add aria-labels to search and filter controls
    - Ensure table has proper heading
    - Keyboard navigation for table rows
    - Screen reader support for badges
    - Focus management for modal/subtab actions

ALTERNATIVE APPROACH (If DataTable too complex):
Implement expandable card list instead:

<template for:each={activeLocations} for:item="location" key={location.Id}>
  <div class="location-card">
    <div class="location-header" onclick={handleToggleExpand}>
      <span class="location-name">{location.Name}</span>
      <span class="primary-badge" if:true={location.PRM_Primary__c}>Primary</span>
      <div class="actions">
        <lightning-button-icon icon-name="utility:edit" 
                              onclick={handleEditLocation}></lightning-button-icon>
        <lightning-button-icon icon-name="utility:close" 
                              onclick={handleRemoveLocation}></lightning-button-icon>
      </div>
    </div>
    <div class="location-details" if:true={location.expanded}>
      <div>Address: {location.Address1}, {location.City}, {location.State} {location.Zip}</div>
      <div>Phone: {location.Phone}</div>
      <div>Telehealth: {location.PRM_TelehealthOnly__c}</div>
    </div>
  </div>
</template>

OUTPUT:
Provide:
1. Updated prmAddressGroupManager.html with lightning-datatable
2. Updated prmAddressGroupManager.js with data table methods
3. Column definitions array
4. Data transformation logic
5. Sorting/filtering implementations
6. CSS for table styling and badges
7. Comparison of approaches (DataTable vs Expandable Cards)
8. Performance optimization strategies
9. Migration guide from current list view
10. Accessibility checklist
```

---

## 🎨 Visual Comparison: Current vs. Proposed

### **Current State (Screenshot provided)**

```
┌─────────────────────────────────────────────────────────────────┐
│ Active Locations | Pending Locations | Add New                  │
├─────────────────────────────────────────────────────────────────┤
│ ℹ️ Active locations cannot be edited, but can be removed.      │
│    Primary location cannot be removed.                          │
│                                                                 │
│ ROBERT WOOD JOHNSON UNIVERSITY HOSPITAL AT HAMILTON             │
│ (1 Hamilton Health PI-8704)                              Primary │
│ PO Box 48025, Newark, NJ 07101                                 │
│ Phone: 7329238704                        Fax: [empty]          │
│                                                                 │
│ ─────────────────────────────────────────────────────────────── │
│                                                                 │
│ RWJ University Hospital- Rahway(865 Stone St-4200) Primary     │
│ PO Box 1515, Elizabeth, NJ 07207                               │
│ Phone: 2159999999                        Fax: [empty]          │
│                                                                 │
│ ─────────────────────────────────────────────────────────────── │
│                                                                 │
│ St Francis Medical Center(601 Hamilton Ave-5000)      Primary   │
│ PO Box 827800, Philadelphia, PA 19182                          │
│ Phone: 2159999999                        Fax: [empty]          │
│                                    [Scrolls down...]             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### **Proposed: DataTable Approach**

```
┌────────────────────────────────────────────────────────────────────┐
│ Active Locations | Pending Locations | Add New                     │
├────────────────────────────────────────────────────────────────────┤
│ [Search: ____________] [Show: 10 ▼] [Primary Only] [Sort ▼]      │
├────────────────────────────────────────────────────────────────────┤
│ # │ Location Name        │ Address/City   │ Primary│Phone   │Act  │
├────────────────────────────────────────────────────────────────────┤
│ 1 │ Robert Wood J...     │ PO Box 48025.. │   ☑   │ 732... │ ⋮   │
│ 2 │ RWJ University...    │ PO Box 1515... │   ☑   │ 215... │ ⋮   │
│ 3 │ St Francis Medical   │ PO Box 827800..│   ☑   │ 215... │ ⋮   │
│ 4 │ [Location 4]         │ [Address 4]    │   ☐   │ [Phone]│ ⋮   │
│ 5 │ [Location 5]         │ [Address 5]    │   ☐   │ [Phone]│ ⋮   │
│ 6 │ [Location 6]         │ [Address 6]    │   ☐   │ [Phone]│ ⋮   │
│ 7 │ [Location 7]         │ [Address 7]    │   ☐   │ [Phone]│ ⋮   │
│ 8 │ [Location 8]         │ [Address 8]    │   ☐   │ [Phone]│ ⋮   │
│ 9 │ [Location 9]         │ [Address 9]    │   ☐   │ [Phone]│ ⋮   │
│10 │ [Location 10]        │ [Address 10]   │   ☐   │ [Phone]│ ⋮   │
├────────────────────────────────────────────────────────────────────┤
│ Showing 1-10 of 47 locations  [< Prev] [1] [2] [3] [4] [5] [Next >]│
└────────────────────────────────────────────────────────────────────┘
```

### **Proposed: Expandable Card Approach (Alternative)**

```
┌────────────────────────────────────────────────────────────────────┐
│ Active Locations | Pending Locations | Add New                     │
├────────────────────────────────────────────────────────────────────┤
│ [Search: ____________]  Showing 47 active locations                │
├────────────────────────────────────────────────────────────────────┤
│ ▼ ROBERT WOOD JOHNSON HOSPITAL - HAMILTON          Primary [Edit][×]│
│   PO Box 48025, Newark, NJ 07101                                   │
│   Phone: 7329238704 | Telehealth: No                               │
│                                                                    │
│ ► RWJ UNIVERSITY HOSPITAL - RAHWAY                 Primary [Edit][×]│
│   Phone: 2159999999                                                │
│                                                                    │
│ ► ST FRANCIS MEDICAL CENTER                        Primary [Edit][×]│
│   Phone: 2159999999                                                │
│                                                                    │
│ ► [Location 4]                                           [Edit][×] │
│   [Details visible only when expanded]                             │
│                                                                    │
│ [Load More...] (Load next 10)                                      │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Comparison: Recommended Approaches

| Aspect | DataTable | Expandable Cards |
|--------|-----------|------------------|
| **Scalability** | 50+ locations ✅ | 50+ locations ✅ |
| **Space Efficiency** | Excellent (compact) | Good (expandable) |
| **Scannability** | Excellent (column view) | Good (card view) |
| **Sorting** | Built-in ✅ | Manual implementation |
| **Filtering** | Built-in ✅ | Manual implementation |
| **Mobile Responsive** | Requires work | Natural |
| **Learning Curve** | Low (Lightning component) | Low (custom HTML) |
| **Performance** | Excellent | Excellent |
| **Accessibility** | Built-in WCAG | Needs attention |
| **Implementation Time** | 2-3 days | 1-2 days |

**Recommendation:** Use **Lightning DataTable** for the primary approach, with **Expandable Cards** as a fallback for mobile.

---

## 📝 Implementation Steps Summary

### **Phase 1: Subtab Navigation (3-4 Days)**

1. ✅ Modify HTML structure for subtab layout
2. ✅ Create state management for subtab mode
3. ✅ Implement edit methods (handleEditLocation, handleValidateAddress)
4. ✅ Implement action methods (handleUseRecommendedAddress, etc.)
5. ✅ Add CSS for subtab styling
6. ✅ Test all navigation flows
7. ✅ Test accessibility (keyboard, screen reader)
8. ✅ Test responsive design

### **Phase 2: DataTable for Active Locations (2-3 Days)**

1. ✅ Design column definitions
2. ✅ Implement data transformation logic
3. ✅ Add lightning-datatable to HTML
4. ✅ Implement sorting handler
5. ✅ Implement row action handler
6. ✅ Add search/filter functionality
7. ✅ Add pagination
8. ✅ Style for responsive design
9. ✅ Test with 50+ records
10. ✅ Performance optimization

### **Phase 3: Optional Enhancements (1-2 Days)**

1. ✅ Add export to CSV
2. ✅ Add bulk actions
3. ✅ Add advanced filtering
4. ✅ Add date range filtering
5. ✅ Mobile optimization

---

## 🎯 Success Criteria

**Subtab Navigation:**
- ✅ Users can edit address without modal overlay
- ✅ Users can navigate back to list seamlessly
- ✅ Unsaved changes warning works
- ✅ All async operations show loading state
- ✅ WCAG 2.1 AA accessibility compliant

**DataTable for Locations:**
- ✅ 50+ locations load without performance issues
- ✅ Sorting works on all sortable columns
- ✅ Search filters correctly across fields
- ✅ Pagination reduces initial load
- ✅ Mobile view is responsive and usable
- ✅ Users prefer this over scrolling list (UAT feedback)

---

## 📞 Questions for Clarification

Before implementation, confirm:

1. **Subtab Approach:** Is breadcrumb style navigation acceptable, or preferred?
2. **DataTable Columns:** Should we display all fields or just key ones (Name, Address, Primary, Phone)?
3. **Pagination:** Prefer built-in infinite scroll or manual next/previous?
4. **Search:** Should search include phone numbers and addresses, or just location name?
5. **Filters:** Any specific filters beyond "Primary Only" / "Telehealth Only"?
6. **Mobile:** Should mobile use DataTable with horizontal scroll, or switch to cards?
7. **Bulk Actions:** Should we support bulk remove/archive in future?

---

*End of Feature Enhancement Specification*

