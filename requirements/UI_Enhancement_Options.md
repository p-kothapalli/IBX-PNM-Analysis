# UI Enhancement Options - Address Group Manager

## Current Problem

The "Add New Location" button is positioned at the **bottom** of the modal, below the "Existing Practice Locations" section. This creates poor UX:

❌ Users must scroll past all existing locations (could be 10+) to add a new one  
❌ Primary action (Add New) is buried and hard to discover  
❌ Long vertical scroll in modal reduces usability  
❌ The button toggles a form inline, making the modal even longer  

---

## User Workflow Context

### Current Flow:
1. User opens modal via "Update / Edit Address Details" button
2. Modal shows **Existing Practice Locations** first (Active/Pending tabs)
3. User scrolls down past all existing locations
4. Clicks **"Add New Location"** button
5. Group search section expands inline
6. User fills NPI, Tax ID, searches for addresses
7. Selects address from results
8. Location details form appears
9. Scrolls to bottom to click **"Create Location"**

**Total scroll distance:** Can be 1000-2000px depending on existing locations

---

## UI Enhancement Options

### ✅ **Option 1: Add "Add New Location" as Third Tab** (RECOMMENDED)

Convert the add-new workflow into a dedicated tab alongside Active/Pending.

#### Visual Structure:
```
┌─────────────────────────────────────────────────────────┐
│  Enter Group Information                           [X]  │
├─────────────────────────────────────────────────────────┤
│  [Search Locations: ___________________]                │
│                                                         │
│  [Active Locations] [Pending Locations] [➕ Add New]   │
│  ───────────────────────────────────────────────       │
│                                                         │
│  ┌─ Add New Practice Location ──────────────────┐      │
│  │                                               │      │
│  │  Group NPI:  [__________]                     │      │
│  │  Tax ID:     [__________]                     │      │
│  │  Group Name: [▼ Search...]                    │      │
│  │                                               │      │
│  │  [Cancel] [Search for Addresses]              │      │
│  └───────────────────────────────────────────────┘      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### Changes Required:
- Move "Add New Location" section into its own tab
- Tab label: "➕ Add New" or "Add Location"
- Remove the toggle button
- Group search, results, and location form all live in this tab
- Search bar at top works across all tabs

#### Pros:
✅ **No scrolling required** - each tab is self-contained  
✅ **Clear mental model** - tabs separate "view/edit" from "add new"  
✅ **Follows existing pattern** - users already understand tabs  
✅ **Most common action easily accessible** - just one click to add mode  
✅ **Cleaner modal height** - no vertical expansion  

#### Cons:
⚠️ Adds another tab (3 tabs might feel crowded)  
⚠️ User must click tab to add (one extra click vs. visible button)  

#### Implementation Effort: **Low**
- Add new `<lightning-tab>` in existing tabset
- Move add-new section inside the tab
- Remove toggle button/logic

---

### ⚙️ **Option 2: Sticky Header with "Add New" Button**

Keep existing layout but add a prominent "Add New Location" button in the modal header.

#### Visual Structure:
```
┌─────────────────────────────────────────────────────────┐
│  Enter Group Information        [➕ Add New Location] [X]│
├─────────────────────────────────────────────────────────┤
│  [Search Locations: ___________________]                │
│                                                         │
│  [Active Locations] [Pending Locations]                 │
│  ─────────────────────────────────                      │
│                                                         │
│  Active location cards...                               │
│  ...                                                    │
│                                                         │
└─────────────────────────────────────────────────────────┘

When "Add New Location" clicked → Opens SECOND modal on top
```

#### Changes Required:
- Add "Add New Location" button in modal header (next to title)
- Clicking opens a **separate modal** for the add-new workflow
- Or: replace modal content entirely (mode switch)

#### Pros:
✅ **Always visible** - button in header, no scrolling  
✅ **Clear hierarchy** - primary action prominently displayed  
✅ **Separate workflows** - view/edit vs. add kept distinct  
✅ **Follows FAB pattern** - common in modern UIs  

#### Cons:
⚠️ **Modal within modal** if using separate modal (can feel heavy)  
⚠️ **Mode switching** if replacing content (might confuse users)  
⚠️ Header might feel crowded with button + close icon  

#### Implementation Effort: **Medium**
- Add button to modal header
- Handle modal stacking or content replacement
- Add navigation logic (back button if mode switching)

---

### 🔄 **Option 3: Segmented Control (Manage / Add New)**

Add a segmented button at top of modal to switch between two distinct modes.

#### Visual Structure:
```
┌─────────────────────────────────────────────────────────┐
│  Address & Group Management                        [X]  │
├─────────────────────────────────────────────────────────┤
│  [ Manage Existing ] [ ➕ Add New Location ]            │
│  ═══════════════════                                    │
│                                                         │
│  [Search Locations: ___________________]                │
│                                                         │
│  [Active Locations] [Pending Locations]                 │
│  ...existing location content...                        │
│                                                         │
└─────────────────────────────────────────────────────────┘

When "Add New" clicked → Same modal, different content:
┌─────────────────────────────────────────────────────────┐
│  Address & Group Management                        [X]  │
├─────────────────────────────────────────────────────────┤
│  [ Manage Existing ] [ ➕ Add New Location ]            │
│                      ════════════════════               │
│                                                         │
│  ┌─ Add New Practice Location ──────────────────┐      │
│  │  Group NPI:  [__________]                     │      │
│  │  Tax ID:     [__________]                     │      │
│  │  Group Name: [▼ Search...]                    │      │
│  └───────────────────────────────────────────────┘      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### Changes Required:
- Add `<lightning-button-group>` or custom segmented control at top
- Two modes: "Manage Existing" and "Add New Location"
- Content swaps based on selected mode
- Use conditional rendering (`if:true/false`)

#### Pros:
✅ **Clear separation of workflows** - manage vs. add  
✅ **No scrolling needed** - full modal for each mode  
✅ **Single modal** - no complexity of nested modals  
✅ **Reduces cognitive load** - only show relevant UI  

#### Cons:
⚠️ Hides existing locations when adding new (might want to reference them)  
⚠️ Adds another level of navigation (mode switching)  
⚠️ Requires "back" behavior if user starts adding but wants to check existing first  

#### Implementation Effort: **Medium-High**
- Add segmented control component
- Refactor modal body with conditional rendering
- Handle state management for mode switching

---

### 🎯 **Option 4: "Quick Add" Card in Pending Tab**

Add a special "+ Add New Location" card at the **top** of the Pending Locations tab.

#### Visual Structure:
```
┌─────────────────────────────────────────────────────────┐
│  [Active Locations] [Pending Locations]                 │
│                     ──────────────────                  │
│  [Search: ___________________]                          │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  ➕ Add New Practice Location                    │   │
│  │                                                  │   │
│  │  Click to add a new location to this group      │   │
│  │                                    [+ Add New]   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─ Pending Location 1 ─────────────────────────────┐  │
│  │  Practice Name: [__________]                      │  │
│  │  ...editable fields...                            │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘

Clicking "+ Add New" → Inline expansion or modal
```

#### Changes Required:
- Add special "add new" card at top of Pending Locations list
- Clicking opens inline form or separate modal
- Visually distinct (different color, + icon)

#### Pros:
✅ **Contextual placement** - new locations are "pending" initially  
✅ **Minimal change** - fits existing structure  
✅ **Always visible** when on Pending tab  

#### Cons:
⚠️ Requires users to know to look in Pending tab  
⚠️ Mixes "add new" with "edit pending" (might be confusing)  
⚠️ Inline expansion still causes scrolling if form is long  
⚠️ Not visible from Active Locations tab  

#### Implementation Effort: **Low-Medium**
- Add card component at top of pending list
- Handle expansion/modal logic
- Style to differentiate from regular pending cards

---

## Comparison Matrix

| Criteria | Option 1: Tab | Option 2: Header Button | Option 3: Segmented | Option 4: Card in Pending |
|----------|---------------|------------------------|---------------------|--------------------------|
| **Discoverability** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **No Scrolling** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Workflow Clarity** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Fits Existing Pattern** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Implementation Effort** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| **User Efficiency** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |

---

## Recommendation

### 🏆 **Option 1: Add "Add New Location" as Third Tab**

**Why this is best:**
1. ✅ **Lowest implementation effort** - just restructure existing code
2. ✅ **Fits existing mental model** - users already using tabs
3. ✅ **Solves core problem** - no scrolling, primary action easily accessible
4. ✅ **Clean separation** - view/edit existing vs. add new
5. ✅ **No new patterns to learn** - uses familiar tab interface

**Quick Win Variant:** Use icon in tab label to save space
- Tab 1: "Active (5)" with green dot
- Tab 2: "Pending (2)" with orange dot  
- Tab 3: "➕ Add New" with plus icon

---

## Additional Enhancements (Any Option)

Regardless of which option you choose, consider these improvements:

### 1. **Sticky Search Bar**
- Keep the location search bar fixed at top of modal
- Works across all tabs/modes
- Users can quickly filter while switching between tabs

### 2. **Counter Badges on Tabs**
```
[Active Locations (5)] [Pending Locations (2)] [➕ Add New]
```

### 3. **Progressive Disclosure in Add New**
Instead of showing all fields at once:
- **Step 1:** Group NPI, Tax ID, Name → Search button
- **Step 2:** Search Results (only show after search)
- **Step 3:** Location Details form (only show after selecting)

This reduces visual complexity and guides users through the flow.

### 4. **Success Feedback**
After creating a new location:
- Auto-switch to Pending tab
- Highlight the newly created location
- Show toast: "Location added successfully! Review details in Pending Locations tab."

### 5. **Keyboard Shortcuts**
- `Ctrl/Cmd + N` → Jump to Add New tab/mode
- `Ctrl/Cmd + S` → Save pending location
- `Ctrl/Cmd + F` → Focus search bar

---

## Next Steps

1. **Choose preferred option** (recommendation: Option 1)
2. **Review mockups/wireframes** if needed
3. **Implement changes** to HTML structure
4. **Update JavaScript** handlers for new layout
5. **Test user flow** end-to-end
6. **Deploy to qa-sandbox**

---

## Implementation Notes for Option 1

### Files to Modify:
- `prmAddressGroupManager.html` - Add new tab, move add-new section
- `prmAddressGroupManager.js` - Update state management (remove toggle logic)

### Changes Required:

#### HTML Changes:
```html
<lightning-tabset>
    <!-- Existing Active Tab -->
    <lightning-tab label="Active Locations" title="Active Locations">
        ...existing active locations...
    </lightning-tab>
    
    <!-- Existing Pending Tab -->
    <lightning-tab label="Pending Locations" title="Pending Locations">
        ...existing pending locations...
    </lightning-tab>
    
    <!-- NEW: Add New Location Tab -->
    <lightning-tab label="➕ Add New" title="Add New Location">
        <div class="slds-p-around_medium">
            <!-- Move entire "Add New Location" section here -->
            <!-- Group NPI, Tax ID, Name fields -->
            <!-- Search button -->
            <!-- Search results section -->
            <!-- Location details form -->
            <!-- Create button -->
        </div>
    </lightning-tab>
</lightning-tabset>
```

#### JavaScript Changes:
- Remove `showAddNewLocation` boolean
- Remove `handleAddNewLocation()` toggle handler
- Remove `handleCancelAddNewLocation()` cancel handler
- Add `activeTab` property to track current tab
- Add `handleTabChange()` to clear form when switching tabs

**Estimated Time:** 1-2 hours

---

**Created:** April 12, 2026  
**Status:** Awaiting user decision
