# User Story: Make Notes Field Optional on PAR App Review, PSV, and QC Flows

## Story

**As a** Provider Network Operations team member reviewing Provider Applications  
**I want** the Notes field to be optional (not required) on the App Review, PSV, and QC flows  
**So that** I can complete my review workflow efficiently without being forced to add notes when I have no additional information to document

---

## Business Context

Users are currently blocked from progressing through the Provider Application Review (PAR) workflows when the Notes field is mandatory but they have no meaningful content to add. This creates friction in the review process and reduces operational efficiency. Making the field optional while keeping it available allows users to add notes when relevant without creating unnecessary barriers.

---

## Acceptance Criteria

### Scenario 1: App Review Flow - Optional Notes
- **Given** I am on the App Review flow in the PAR form
- **When** I leave the Notes field blank and attempt to proceed to the next step
- **Then** the system should allow me to continue without displaying a validation error
- **And** I should not be required to enter any text in the Notes field

### Scenario 2: PSV Flow - Optional Notes
- **Given** I am on the Primary Source Verification (PSV) flow in the PAR form
- **When** I leave the Notes field blank and attempt to proceed to the next step
- **Then** the system should allow me to continue without displaying a validation error
- **And** I should not be required to enter any text in the Notes field

### Scenario 3: QC Flow - Optional Notes
- **Given** I am on the Quality Control (QC) flow in the PAR form
- **When** I leave the Notes field blank and attempt to proceed to the next step
- **Then** the system should allow me to continue without displaying a validation error
- **And** I should not be required to enter any text in the Notes field

### Scenario 4: Notes Still Captured When Provided
- **Given** I am on any of the three affected flows (App Review, PSV, or QC)
- **When** I voluntarily enter text in the Notes field and proceed
- **Then** the notes should be saved successfully to the appropriate record
- **And** the data should be available for future reference and reporting

### Scenario 5: Validation Error Removed
- **Given** I am on any of the three affected flows
- **When** I view the Notes field
- **Then** there should be no visual indicator (asterisk, "required" label) showing the field as mandatory
- **And** no validation error message should appear when the field is left blank

---

## Technical Implementation

### OmniScript Configuration Changes

**Location:** Provider Application Review OmniScript(s)  
**Component Type:** Text Input / Text Area elements for Notes field

1. **Identify OmniScript(s):**
   - App Review Flow OmniScript
   - PSV Flow OmniScript
   - QC Flow OmniScript
   - *Note: These may be separate OmniScripts or steps within a single PAR OmniScript*

2. **Field Property Updates (for each flow):**
   - Navigate to the Notes field element in each affected step/flow
   - Set `Required` property to `FALSE` (unchecked)
   - Remove any conditional Required rules if present
   - Verify `Response JSON Path` is correctly configured for data capture

3. **Custom Validation Rules:**
   - Review and remove any custom JavaScript validation in the OmniScript that enforces Notes as required
   - Check for validation rules in:
     - Element-level validation
     - Step-level validation
     - Custom LWC components (if used for the Notes field)

4. **Save Actions / DataRaptors:**
   - Verify that the Extract/Transform DataRaptors handling Notes field can accept null/blank values
   - Confirm field mappings don't have "Required" flags set at the DataRaptor level
   - Test that blank Notes values save correctly to the underlying Salesforce object

5. **Integration Procedures:**
   - If an Integration Procedure processes the PAR form data, verify it handles null/empty Notes values gracefully
   - Update error handling to not flag blank Notes as an error condition

### Affected Salesforce Objects
- **Likely Object:** Custom object related to Provider Application or Review records (e.g., `Provider_Application__c`, `PAR_Review__c`, or similar)
- **Field:** Notes__c (or similar field name)
- **Action:** Verify field-level security and validation rules on the object don't conflict with making the field optional

### Validation Rules on Object
- Check for Salesforce validation rules on the Notes field that might enforce Required status
- Deactivate or update any validation rules that prevent blank Notes on these specific review flows

---

## Dependencies

- Access to OmniStudio environment (Dev/Sandbox) for configuration changes
- Knowledge of exact OmniScript names for the three flows
- Confirmation of underlying Salesforce object and field names
- Understanding of data model for Provider Application Review process
- QA environment access for testing all three flows

---

## Assumptions

1. The Notes field currently has the Required checkbox enabled at the OmniScript element level
2. There are no business-critical audit requirements mandating notes for compliance purposes
3. The three flows (App Review, PSV, QC) are distinct steps/flows within the PAR process
4. No downstream systems or reports require Notes to be populated for these specific flows
5. Historical data with populated Notes will remain unchanged
6. Making the field optional doesn't impact any SLAs or audit trail requirements
7. No compensation or decision logic depends on Notes being populated

---

## Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| Compliance or audit requirements mandate documentation | Confirm with Compliance team that optional notes are acceptable; consider conditional required logic for rejection scenarios |
| Data quality degradation over time | Monitor usage patterns post-deployment; add helpful placeholder text to encourage note entry when relevant |
| Multiple active OmniScript versions | Query metadata to identify all active versions and update consistently; deactivate old versions if appropriate |
| Conditional required logic elsewhere in form | Perform thorough testing of entire form flow, not just the Notes field in isolation |

---

## Effort Estimation

**Story Points:** 3  
**Estimated Hours:** 4-6 hours

### Breakdown:

| Task | Estimate |
|------|----------|
| Discovery & Analysis (identify OmniScripts, locate fields, review DataRaptors/IPs, check validation rules) | ~1 hour |
| Configuration Changes (update Required property in 3 flows, update conditional validation logic, verify DataRaptor mappings) | ~1-2 hours |
| Testing (test all 3 flows with blank/populated Notes, verify no validation errors, test related conditional logic) | ~1.5-2 hours |
| Documentation & Deployment (update docs, create deployment package, deploy, communicate changes) | ~0.5-1 hour |

**Complexity Factors:**
- Low complexity if all three flows are steps in a single OmniScript
- Medium complexity if flows are separate OmniScripts requiring multiple updates
- Additional effort required if conditional logic or audit requirements are discovered

---

## Test Scenarios

### Happy Path Testing
1. Complete App Review flow with blank Notes field - Success
2. Complete PSV flow with blank Notes field - Success
3. Complete QC flow with blank Notes field - Success
4. Complete all three flows with populated Notes - Notes saved correctly

### Edge Cases
5. Enter Notes, delete all text, proceed - Should allow blank submission
6. Enter only whitespace in Notes field - Should handle gracefully
7. Enter maximum character length in Notes - Should save successfully
8. Switch between flows with Notes entered in one - Data should not bleed between flows

### Regression Testing
9. Other required fields still enforce validation - Validation intact
10. Complete PAR workflow end-to-end - Process completes successfully
11. Review saved records in Salesforce - Notes field shows null/blank correctly
12. Run any existing reports that reference Notes - Reports handle null values

---

## Definition of Done

- [ ] Required property removed from Notes field in all three OmniScript flows
- [ ] No validation errors appear when Notes field is left blank
- [ ] Notes field still captures and saves data when user voluntarily provides input
- [ ] No visual required indicator (asterisk) displayed on Notes field
- [ ] All test scenarios pass in Dev/Sandbox environment
- [ ] Code review completed (if any custom validation logic removed)
- [ ] Changes deployed to Production
- [ ] User acceptance testing completed by business stakeholders
- [ ] User documentation updated (if applicable)
- [ ] Release notes created and communicated to operations team

---

## Additional Notes

- **Change Management:** Consider notifying users that Notes are now optional, as they may be accustomed to the current behavior
- **Future Enhancement:** If data quality becomes a concern, consider implementing contextual help text or tooltips to guide users on when notes are valuable
- **Reporting Impact:** Verify that existing reports or dashboards that display Notes can handle null values appropriately

---

**Priority:** Medium  
**Sprint:** TBD  
**Component:** OmniStudio - Provider Network Management  
**Labels:** PAR, OmniScript, Field-Validation, Provider-Operations
