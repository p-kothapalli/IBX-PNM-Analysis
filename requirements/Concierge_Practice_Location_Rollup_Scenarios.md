# Concierge Provider - Practice Location Rollup Logic Scenarios

**Document Version:** 1.0  
**Created Date:** April 5, 2026  
**Purpose:** Define all scenarios for creating/terminating Practice Location-level Info Code Assignments based on practitioner changes

---

## Business Rule

**Practice Location-level Info Code Assignment should exist when:**
- ALL practitioners at that location are Concierge Providers
- At least one practitioner exists at the location

**Effective Date Logic:**
- Effective Date = The date when the condition became TRUE (all practitioners became concierge)
- Termination Date = The date when the condition became FALSE (at least one non-concierge practitioner exists)

---

## Comprehensive Scenario Table

| # | Scenario | Initial State | Action/Trigger | Result State | Practice Location Info Code Assignment Action | Effective/Termination Date | Notes |
|---|----------|---------------|----------------|--------------|----------------------------------------------|----------------------------|-------|
| **1. Adding Practitioners** |
| 1.1 | First concierge practitioner joins empty location | Location: 0 practitioners | Concierge PCP joins (join date: 01/01/2026) | Location: 1 concierge | **CREATE** assignment | Effective Date = 01/01/2026 | Location now has 100% concierge (1 of 1) |
| 1.2 | Concierge practitioner joins location with only concierge practitioners | Location: 3 concierge | 4th concierge joins (join date: 02/01/2026) | Location: 4 concierge | **NO CHANGE** (assignment already exists) | N/A | Location remains 100% concierge |
| 1.3 | Non-concierge practitioner joins location with only concierge practitioners | Location: 3 concierge (assignment exists) | Specialist (non-concierge) joins (join date: 03/01/2026) | Location: 3 concierge + 1 non-concierge | **TERMINATE** existing assignment | Termination Date = 03/01/2026 | Location no longer 100% concierge (3 of 4) |
| 1.4 | Concierge practitioner joins location with mixed practitioners | Location: 2 concierge + 1 non-concierge (no assignment) | 3rd concierge joins (join date: 04/01/2026) | Location: 3 concierge + 1 non-concierge | **NO ACTION** | N/A | Still not 100% concierge (3 of 4) |
| 1.5 | First non-concierge practitioner joins empty location | Location: 0 practitioners | Specialist joins (join date: 05/01/2026) | Location: 1 non-concierge | **NO ACTION** | N/A | Not 100% concierge |
| **2. Removing Practitioners** |
| 2.1 | Last non-concierge practitioner leaves location with mixed practitioners | Location: 4 concierge + 1 specialist (no assignment) | Specialist terminated (term date: 06/01/2026) | Location: 4 concierge | **CREATE** assignment | Effective Date = 06/01/2026 | Location now 100% concierge (4 of 4) |
| 2.2 | Concierge practitioner leaves location with only concierge practitioners | Location: 5 concierge (assignment exists) | 1 concierge terminated (term date: 07/01/2026) | Location: 4 concierge | **NO CHANGE** (assignment continues) | N/A | Location remains 100% concierge (4 of 4) |
| 2.3 | Last practitioner (concierge) leaves location | Location: 1 concierge (assignment exists) | Last concierge terminated (term date: 08/01/2026) | Location: 0 practitioners | **TERMINATE** assignment | Termination Date = 08/01/2026 | No practitioners remaining |
| 2.4 | Non-concierge practitioner leaves location with mixed practitioners | Location: 2 concierge + 2 non-concierge (no assignment) | 1 non-concierge terminated (term date: 09/01/2026) | Location: 2 concierge + 1 non-concierge | **NO ACTION** | N/A | Still not 100% concierge (2 of 3) |
| 2.5 | Multiple non-concierge practitioners leave simultaneously, leaving only concierge | Location: 3 concierge + 3 non-concierge (no assignment) | 3 non-concierge terminated (term date: 10/01/2026) | Location: 3 concierge | **CREATE** assignment | Effective Date = 10/01/2026 | Location now 100% concierge |
| **3. Practitioner Status Changes** |
| 3.1 | Last non-concierge practitioner converts to concierge | Location: 3 concierge + 1 non-concierge (no assignment) | Non-concierge becomes concierge (change date: 11/01/2026) | Location: 4 concierge | **CREATE** assignment | Effective Date = 11/01/2026 | Location now 100% concierge |
| 3.2 | Concierge practitioner loses concierge status at location | Location: 4 concierge (assignment exists) | 1 concierge loses status (change date: 12/01/2026) | Location: 3 concierge + 1 non-concierge | **TERMINATE** assignment | Termination Date = 12/01/2026 | No longer 100% concierge |
| 3.3 | Non-concierge practitioner gains concierge status but others still non-concierge | Location: 1 concierge + 3 non-concierge (no assignment) | 1 non-concierge becomes concierge (change date: 01/15/2026) | Location: 2 concierge + 2 non-concierge | **NO ACTION** | N/A | Still not 100% concierge (2 of 4) |
| **4. Bulk Changes** |
| 4.1 | All practitioners at location gain concierge status simultaneously | Location: 5 non-concierge (no assignment) | All 5 become concierge (change date: 02/15/2026) | Location: 5 concierge | **CREATE** assignment | Effective Date = 02/15/2026 | Location now 100% concierge |
| 4.2 | All concierge practitioners at location lose concierge status | Location: 4 concierge (assignment exists) | All 4 lose concierge status (change date: 03/15/2026) | Location: 4 non-concierge | **TERMINATE** assignment | Termination Date = 03/15/2026 | No concierge practitioners |
| 4.3 | Multiple practitioners join/leave same day, result is 100% concierge | Location: 2 concierge + 2 non-concierge (no assignment) | Same day: 2 non-concierge leave + 3 concierge join (date: 04/15/2026) | Location: 5 concierge | **CREATE** assignment | Effective Date = 04/15/2026 | Net result: 100% concierge |
| **5. Practice Location Lifecycle** |
| 5.1 | New practice location opens with all concierge practitioners | Location: New | Location opens with 3 concierge (open date: 05/15/2026) | Location: 3 concierge | **CREATE** assignment | Effective Date = 05/15/2026 | 100% concierge from day 1 |
| 5.2 | New practice location opens with mixed practitioners | Location: New | Location opens with 2 concierge + 1 non-concierge (open date: 06/15/2026) | Location: 2 concierge + 1 non-concierge | **NO ACTION** | N/A | Not 100% concierge |
| 5.3 | Practice location closes with active concierge assignment | Location: 3 concierge (assignment exists) | Location closes (close date: 07/15/2026) | Location: Closed | **TERMINATE** assignment | Termination Date = 07/15/2026 | Location no longer active |
| **6. Edge Cases** |
| 6.1 | Practitioner has concierge at one location but not another | Location A: 3 concierge (assignment exists)<br>Location B: 2 concierge + 1 non-concierge (no assignment) | Practitioner with concierge at A joins B (join date: 08/15/2026) | Location A: unchanged<br>Location B: 3 concierge + 1 non-concierge | **NO ACTION** on either location | N/A | Practitioner-level status doesn't auto-apply to new location |
| 6.2 | Retroactive effective date for historical correction | Location: 4 concierge (assignment exists with effective date 01/01/2026) | Admin discovers location was 100% concierge since 12/01/2025 | Location: 4 concierge | **UPDATE** assignment | Update Effective Date = 12/01/2025 | Historical correction |
| 6.3 | Practitioner location assignment ends but not terminated | Location: 4 concierge (assignment exists) | 1 concierge's location assignment ends (end date: 09/15/2026) | Location: 3 concierge | **NO CHANGE** (still 100% concierge) | N/A | Location remains 100% concierge |
| 6.4 | Practitioner has multiple roles at same location (PCP + Specialist) | Location: 3 concierge PCPs + 1 practitioner (PCP concierge + Specialist non-concierge) | No change | Location: Unclear if 100% concierge | **BUSINESS DECISION NEEDED** | TBD | Does dual role count as concierge or mixed? |
| **7. Timing Scenarios** |
| 7.1 | Future-dated practitioner join makes location 100% concierge | Location: 3 concierge + 1 non-concierge (no assignment) | Non-concierge practitioner future-dated termination (effective 10/01/2026) | Location: Will be 3 concierge on 10/01/2026 | **CREATE** assignment (on 10/01/2026) | Effective Date = 10/01/2026 | Scheduled change |
| 7.2 | Backdated practitioner termination changes historical status | Location: 4 concierge (assignment exists with effective date 01/01/2026) | Admin backdates non-concierge join to 03/01/2026 | Location: Historical gap in 100% status | **CREATE NEW** assignment with term date 03/01/2026 AND **CREATE SECOND** assignment with effective date = [date non-concierge left] | Complex: may need to split assignment | Historical correction creates gap |
| **8. Data Quality Scenarios** |
| 8.1 | Duplicate practitioner records at same location | Location: 3 unique concierge + 1 duplicate (no assignment) | Admin merges duplicate | Location: 3 concierge | **CREATE** assignment | Effective Date = merge date | Location now correctly 100% concierge |
| 8.2 | Practitioner missing concierge flag but has Practitioner Practice Location assignment | Location: 3 concierge + 1 practitioner (missing flag but has PPL assignment) | Admin discovers missing flag | Location: Unclear if 100% | **BUSINESS RULE NEEDED** | TBD | Source of truth: PPL assignment or practitioner-level flag? |

---

## Implementation Decision Matrix

| Question | Decision | Rationale |
|----------|----------|-----------|
| Should we automatically create Practice Location assignments? | **YES** | Business requested rollup logic for data quality and reporting |
| What is the source of truth for "concierge" status? | **Practitioner Practice Location-level Info Code Assignment** | Most granular; practitioner can be concierge at Location A but not B |
| When multiple changes occur same day, which date wins? | **Use the transaction date** | Simplest; batch jobs run daily |
| Should we handle future-dated changes? | **YES** | Support for scheduled changes (e.g., practitioner joining next month) |
| Should we handle backdated changes? | **YES, with caution** | Historical corrections needed, but may create complex scenarios |
| What if practitioner has dual role (PCP + Specialist)? | **BUSINESS DECISION NEEDED** | Clarify: is location 100% concierge if one practitioner has mixed roles? |
| Should we create assignment for location with 0 practitioners? | **NO** | Assignment requires at least one practitioner |
| Should Practice Location assignment override Practitioner Practice Location assignments? | **NO** | Practitioner Practice Location is source of truth; Practice Location is derived rollup |

---

## Trigger Events for Batch Job

The batch job should run on these events to create/update/terminate Practice Location-level assignments:

1. **HealthcarePractitionerFacility (junction) created**
2. **HealthcarePractitionerFacility (junction) terminated/deleted**
3. **HealthcarePractitionerFacility effective date changed**
4. **HealthcarePractitionerFacility termination date changed**
5. **Practitioner Practice Location-level Info Code Assignment created**
6. **Practitioner Practice Location-level Info Code Assignment terminated**
7. **Practitioner Practice Location-level Info Code Assignment effective date changed**
8. **Practitioner Practice Location-level Info Code Assignment termination date changed**

---

## Recommended Batch Job Logic

```
FOR EACH HealthcareFacility (Practice Location):
    
    // Step 1: Get all practitioners at this location
    List<HealthcarePractitionerFacility> allPractitioners = [
        SELECT Id, PractitionerId, FacilityId, EffectiveDate, TerminationDate
        FROM HealthcarePractitionerFacility
        WHERE FacilityId = :facilityId
        AND (TerminationDate = null OR TerminationDate > TODAY)
    ];
    
    // Step 2: Get all Practitioner Practice Location-level concierge assignments
    List<PRM_InfoCodeAssignment__c> conciergeAssignments = [
        SELECT Id, PRM_PractitionerFacilityAssignment__c, PRM_EffectiveDate__c, PRM_TerminationDate__c
        FROM PRM_InfoCodeAssignment__c
        WHERE PRM_InfoCode__r.Name = 'Concierge Provider'
        AND PRM_PractitionerFacilityAssignment__c IN :allPractitioners
        AND (PRM_TerminationDate__c = null OR PRM_TerminationDate__c > TODAY)
    ];
    
    // Step 3: Check if 100% concierge
    Boolean is100PercentConcierge = (allPractitioners.size() > 0 
                                     AND allPractitioners.size() == conciergeAssignments.size());
    
    // Step 4: Get existing Practice Location-level assignment
    PRM_InfoCodeAssignment__c existingAssignment = [
        SELECT Id, PRM_EffectiveDate__c, PRM_TerminationDate__c
        FROM PRM_InfoCodeAssignment__c
        WHERE PRM_InfoCode__r.Name = 'Concierge Provider'
        AND PRM_HealthcareFacility__c = :facilityId
        AND (PRM_TerminationDate__c = null OR PRM_TerminationDate__c > TODAY)
        LIMIT 1
    ];
    
    // Step 5: Take action based on current vs desired state
    IF (is100PercentConcierge AND existingAssignment == null) {
        // CREATE new assignment
        // Effective Date = TODAY (or most recent trigger date)
        CREATE PRM_InfoCodeAssignment__c with:
            - PRM_HealthcareFacility__c = facilityId
            - PRM_InfoCode__c = 'Concierge Provider'
            - PRM_EffectiveDate__c = [TRIGGER_DATE]
            - PRM_TerminationDate__c = null
    }
    ELSE IF (!is100PercentConcierge AND existingAssignment != null) {
        // TERMINATE existing assignment
        // Termination Date = TODAY (or most recent trigger date)
        UPDATE existingAssignment:
            - PRM_TerminationDate__c = [TRIGGER_DATE]
    }
    ELSE IF (is100PercentConcierge AND existingAssignment != null) {
        // NO ACTION - assignment already exists
    }
    ELSE IF (!is100PercentConcierge AND existingAssignment == null) {
        // NO ACTION - no assignment needed
    }
END FOR
```

---

## Trigger Date Logic

**Business Requirement:** Effective Date should be "whatever date triggered the creation"

**Implementation Options:**

| Option | Trigger Date | Pros | Cons |
|--------|--------------|------|------|
| **Option 1: Use TODAY** | Current date when batch runs | Simple; always accurate as of "now" | Loses precision if batch runs daily |
| **Option 2: Use Transaction Date** | Date of the triggering event (join/term/change) | Precise; reflects actual trigger | Complex; requires tracking trigger event date |
| **Option 3: Use MAX(Effective Date)** | Latest effective date from Practitioner Practice Location assignments | More accurate than TODAY | May not reflect termination triggers |
| **Option 4: Query Last Change Date** | Query audit trail for last change to practitioners at location | Most accurate | Performance impact; complex queries |

**Recommended:** **Option 2 (Transaction Date)** with fallback to TODAY
- Track the trigger date in batch job context
- Use transaction date from HealthcarePractitionerFacility or Info Code Assignment change
- Fall back to TODAY if trigger date unavailable

---

## Example Scenarios with Dates

### Scenario 2.1: Last Non-Concierge Leaves

**Timeline:**
- 01/01/2026: Location has 4 concierge PCPs + 1 specialist (no Practice Location assignment)
- 06/01/2026: Specialist terminated (termination date on HealthcarePractitionerFacility = 06/01/2026)
- 06/02/2026: Batch job runs, detects location is now 100% concierge

**Action:**
- CREATE Practice Location-level Info Code Assignment
- PRM_EffectiveDate__c = **06/01/2026** (specialist termination date = trigger date)

---

### Scenario 3.1: Last Non-Concierge Converts to Concierge

**Timeline:**
- 01/01/2026: Location has 3 concierge + 1 non-concierge
- 11/01/2026: Non-concierge practitioner gains concierge Info Code Assignment at this location (effective date = 11/01/2026)
- 11/02/2026: Batch job runs, detects location is now 100% concierge

**Action:**
- CREATE Practice Location-level Info Code Assignment
- PRM_EffectiveDate__c = **11/01/2026** (new concierge assignment effective date = trigger date)

---

### Scenario 1.3: Non-Concierge Joins All-Concierge Location

**Timeline:**
- 01/01/2026: Location has 3 concierge (Practice Location assignment exists with effective date = 01/01/2026)
- 03/01/2026: Specialist (non-concierge) joins (HealthcarePractitionerFacility effective date = 03/01/2026)
- 03/02/2026: Batch job runs, detects location is no longer 100% concierge

**Action:**
- UPDATE existing Practice Location-level Info Code Assignment
- PRM_TerminationDate__c = **03/01/2026** (specialist join date = trigger date)

---

## Open Questions for Business

1. **Dual Role Practitioners:** If a practitioner has both PCP (concierge) and Specialist (non-concierge) roles at the same location, should the location be considered 100% concierge?

2. **Backdated Changes:** If an admin backdates a practitioner's join/termination, should we:
   - Update historical effective dates (complex, may split existing assignments)?
   - Keep current effective dates (simpler, less accurate)?

3. **Future-Dated Changes:** Should batch job create future-dated assignments, or wait until effective date arrives?

4. **Frequency:** Should batch job run:
   - Real-time (trigger-based)?
   - Daily?
   - Weekly?

5. **Source of Truth:** If Practitioner Practice Location assignment conflicts with practitioner-level checkbox `PRM_IsConciergeProvider__c`, which wins?
   - Recommendation: Practitioner Practice Location assignment (most granular)

---

## Recommended User Story

**Story: Implement Practice Location Rollup Batch for Concierge Info Code Assignments**

**Priority:** P1 - High  
**Story Points:** 8  
**Component:** PIE - Batch Job

**As a** Data Quality Manager  
**I want** Practice Location-level Info Code Assignments to be automatically created when all practitioners at a location are concierge providers  
**So that** reporting and analytics can easily identify concierge practice locations without complex queries

**Acceptance Criteria:**
1. Batch job runs daily (or on trigger) to evaluate all practice locations
2. For each location, calculates if 100% of active practitioners have active Practitioner Practice Location-level concierge assignments
3. Creates Practice Location-level assignment when condition becomes true (effective date = trigger date)
4. Terminates Practice Location-level assignment when condition becomes false (termination date = trigger date)
5. Handles all scenarios in table above
6. Logs actions taken for audit trail
7. Sends notification if errors occur
8. Performance: Processes 10,000+ locations within 30 minutes

---

**End of Document**
