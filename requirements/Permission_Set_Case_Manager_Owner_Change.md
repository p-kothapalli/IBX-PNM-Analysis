# USER STORY 1: Create Lightweight Permission Set for Case Manager Owner Changes

**Persona:** System Administrator, Credentialing Operations Lead  
**Priority:** P0  
**OmniScript:** N/A  
**Integration Procedures:** PRM_ReviewPSVCaseRecordsUpdate, PRM_ReviewParCaseRecordsUpdate, PRM_ReviewRecredCaseRecordsUpdate, PRM_DataUpdationforHAPACCommitteeReview, PRM_DelegatedPractitionerCreation (and related)  
**Relevant Requirements:** PRM_RestrictUsertochangeCaseManagerOwner custom permission gate; Ancillary Reassessment PSV flow permission blocking

---

## Story

**As a** Business Administrator or credentialing process owner,  
**I want** a lightweight, focused permission set that grants only the ability to change Case Manager owners during flow processing,  
**So that** business admins can complete Ancillary Reassessment PSV, PSV QC, PAR Review, and other credentialing flows that reassign case managers, without being forced to receive broader PRM_NetworkManagementQC permissions.

**Why it matters:** Currently, business admins hit a validation rule error ("You do not have necessary permission to change the Case Manager owner") when processing PSV and other flows. The only workaround is to assign `PRM_NetworkManagementQC`, which grants Network Management QC-specific permissions unrelated to their role. This blocks critical P0 flows and forces over-permissioning.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|--------------|-------------|
| Ancillary Reassessment PSV | PRM_AncillaryReassessmentPSV_English | Final submission | PRM_ReviewPSVCaseRecordsUpdate (IP) |
| PSV QC Review | PRM_OffCycleQCReview_English | Case manager reassignment | PRM_ReviewPSVCaseRecordsUpdate (IP) |
| PAR Application Review | PRM_PractitionerParticipationForm_English | Committee routing | PRM_ReviewParCaseRecordsUpdate (IP) |
| Re-Credentialing | PRM_OffCycleCredentialing_English | Case manager update | PRM_ReviewRecredCaseRecordsUpdate (IP) |
| Committee Review | PRM_ReviewHACAC_English | Case owner change post-decision | PRM_DataUpdationforHAPACCommitteeReview (IP) |

---

## Current State (from codebase)

### PRM_RestrictUsertochangeCaseManagerOwner Custom Permission

- **Definition:** Custom permission on `IndividualApplication` object, gated by validation rule `PRM_RestrictUserToChangeTheOwner`
- **Current consumers:** Only `PRM_NetworkManagementQC` permission set
- **Location:** `force-app/main/default/customPermissions/PRM_RestrictUsertochangeCaseManagerOwner.customPermission-meta.xml`

### PRM_NetworkManagementQC Permission Set

- **Current state:** Grants both `PRM_NetworkManagementQCPermission` custom permission AND `PRM_RestrictUsertochangeCaseManagerOwner`
- **Bloat:** Contains Network Management QC-specific permissions (e.g., field access on Account, IndividualApplication) that are not relevant to business admins running other flows
- **Location:** `force-app/main/default/permissionsets/PRM_NetworkManagementQC.permissionset-meta.xml` (lines 76–82)

### Validation Rule

- **Name:** `PRM_RestrictUserToChangeTheOwner`
- **Object:** `IndividualApplication` (Case Manager)
- **Trigger:** When `OwnerId` field changes AND user lacks `PRM_RestrictUsertochangeCaseManagerOwner` custom permission
- **Error message:** "You do not have necessary permission to change the Case Manager owner"

---

## Technical Section (For Developers)

### Changes Required

| Component | Type | Change |
|-----------|------|--------|
| **PRM_AllowCaseManagerOwnerChange** | New Permission Set | Create lightweight permission set containing only `PRM_RestrictUsertochangeCaseManagerOwner` custom permission. No field-level permissions, no object permissions beyond what the user already has. |
| **PRM_NetworkManagementQC** | Permission Set Update | Remove `PRM_RestrictUsertochangeCaseManagerOwner` custom permission (lines 79–82). This custom permission will now be granted only via `PRM_AllowCaseManagerOwnerChange`. |
| **User Role Assignment** | Automation / Setup | Create an automation rule or list custom users who are Business Admins (profile or role-based) to auto-assign `PRM_AllowCaseManagerOwnerChange` upon user creation. Document the manual assignment process for non-standard users. |

### Permission Set Specifications

#### New Permission Set: PRM_AllowCaseManagerOwnerChange

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>Grants permission to change Case Manager (IndividualApplication) record owner during credentialing flow processing. Lightweight — no field or object permissions included.</description>
    <hasActivationRequired>false</hasActivationRequired>
    <label>PRM Allow Case Manager Owner Change</label>
    <license>Salesforce</license>
    <customPermissions>
        <enabled>true</enabled>
        <name>PRM_RestrictUsertochangeCaseManagerOwner</name>
    </customPermissions>
</PermissionSet>
```

#### Update to PRM_NetworkManagementQC

**Remove lines 79–82:**
```xml
    <customPermissions>
        <enabled>true</enabled>
        <name>PRM_RestrictUsertochangeCaseManagerOwner</name>
    </customPermissions>
```

**Rationale:** The Network Management QC permission set should not be the only avenue for granting this critical cross-flow permission. Users with Network Management QC responsibilities can receive `PRM_AllowCaseManagerOwnerChange` as an additional assignment if needed.

---

## Acceptance Criteria

### AC1: Permission Set Created

**Given** a system admin navigates to Setup → Permission Sets,  
**When** searching for "PRM_AllowCaseManagerOwnerChange",  
**Then** the permission set is visible, marked as active, and contains exactly one custom permission: `PRM_RestrictUsertochangeCaseManagerOwner`.

---

### AC2: Business Admin Auto-Assignment

**Given** a new user is created with the profile "Business Administrator" or assigned to the "Business Admin" role,  
**When** the user is saved,  
**Then** the `PRM_AllowCaseManagerOwnerChange` permission set is automatically assigned to the user within 5 minutes (via platform automation, user provisioning process, or manual batch assignment documented in setup guide).

---

### AC3: Validation Rule Bypass Confirmed

**Given** a business admin (who previously could not complete Ancillary Reassessment PSV due to permission error) is assigned `PRM_AllowCaseManagerOwnerChange`,  
**When** that user attempts to submit the PSV flow and a Case Manager owner change is triggered (e.g., at the final decision step of PRM_ReviewPSVCaseRecordsUpdate IP),  
**Then** the validation rule `PRM_RestrictUserToChangeTheOwner` does **not** fire, and the Case Manager owner is successfully updated.

---

### AC4: PRM_NetworkManagementQC Cleaned Up

**Given** the `PRM_RestrictUsertochangeCaseManagerOwner` custom permission is removed from `PRM_NetworkManagementQC`,  
**When** an existing user with only `PRM_NetworkManagementQC` (and without `PRM_AllowCaseManagerOwnerChange`) attempts a Case Manager owner change,  
**Then** the validation rule still blocks the change with the error message, preserving the security gate.

---

### AC5: Backward Compatibility

**Given** existing users assigned `PRM_NetworkManagementQC` before this change,  
**When** the update is deployed,  
**Then** those users can still perform Case Manager owner changes **if and only if** they are also assigned `PRM_AllowCaseManagerOwnerChange` (or if an automated migration script applies it based on role/profile).

---

### AC6: Flows Function End-to-End

**Given** a business admin with `PRM_AllowCaseManagerOwnerChange` initiates one of the following flows:
- Ancillary Reassessment PSV (PRM_AncillaryReassessmentPSV_English)
- PSV QC Review (PRM_OffCycleQCReview_English)
- PAR Application Review (PRM_PractitionerParticipationForm_English) with Committee routing
- Re-Credentialing (PRM_OffCycleCredentialing_English)
- Committee Review (PRM_ReviewHACAC_English)

**When** the flow completes and attempts to update the Case Manager `OwnerId` via the corresponding Integration Procedure (e.g., PRM_ReviewPSVCaseRecordsUpdate),  
**Then** no validation rule error is raised, and the Case Manager owner change succeeds.

---

### AC7: Manual Assignment Documented

**Given** a non-standard user (e.g., contractor, external system admin) needs Case Manager owner change permissions,  
**When** documentation is reviewed (e.g., setup guide or README),  
**Then** clear instructions exist for manually assigning `PRM_AllowCaseManagerOwnerChange` to the user.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Should the auto-assignment use Salesforce **Profile** (e.g., "Business Administrator") or **Role** (e.g., "Business Admin") to identify eligible users? | Auto-assignment logic depends on this; affects scope of users auto-provisioned. | Technical / Ops |
| 2 | Should existing users with `PRM_NetworkManagementQC` be automatically assigned `PRM_AllowCaseManagerOwnerChange` as part of the deployment, or only new Business Admins going forward? | Backward compatibility and change risk; may affect multiple users. | Ops / Change Management |
| 3 | Is there a specific automation tool (Salesforce Flow, Apex, third-party provisioning) to use for auto-assignment, or should this be a manual batch process documented in a setup guide? | Implementation approach; timeline impact. | Technical |
| 4 | Should `PRM_AllowCaseManagerOwnerChange` also be assigned to non-admin personas (e.g., Credentialing Supervisors, PDM Specialists) who may process these flows, or only to business admins? | Scope of permission set distribution; may affect other user roles. | Product / BA |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| **PRM_RestrictUsertochangeCaseManagerOwner** | Custom Permission | LOW | No change to definition or logic; only decoupled from PRM_NetworkManagementQC and bundled into new perm set. |
| **PRM_NetworkManagementQC** | Permission Set | MEDIUM | Removes one custom permission entry. May affect existing users if not migrated. Verify no downstream dependencies on this perm set for other use cases. |
| **PRM_AllowCaseManagerOwnerChange** | Permission Set (New) | MEDIUM | New permission set; no existing dependencies. Used for auto-assignment to Business Admins. |
| **IndividualApplication (Validation Rule)** | Validation Rule | LOW | No changes to the validation rule itself; only the permission gate is reorganized. |
| **Ancillary Reassessment PSV Flow** | OmniScript / IP | MEDIUM | Once permission set is assigned, flow completes without validation errors. Testing required to confirm no regressions. |
| **PSV QC Review Flow** | OmniScript / IP | MEDIUM | Same as above; flow should complete successfully. |
| **PAR Application Review Flow** | OmniScript / IP | MEDIUM | Same as above. |
| **Re-Credentialing Flow** | OmniScript / IP | MEDIUM | Same as above. |
| **Committee Review Flow** | OmniScript / IP | MEDIUM | Same as above. |
| **User Role/Profile Assignment** | Setup / Config | HIGH | Auto-assignment logic or manual process must be correct; incorrect scope could over/under-provision users. Requires clear documentation and testing. |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| **PRM_AllowCaseManagerOwnerChange (create)** | Permission Set XML | S | Simple XML creation with one custom permission entry. ~15 minutes. |
| **PRM_NetworkManagementQC (update)** | Permission Set XML edit | S | Remove 4 lines (custom permission entry). ~10 minutes. |
| **Auto-assignment automation** | Flow / Apex / Provisioning Config | M | Depends on platform used (Salesforce Flow, Apex, HR provisioning system). Est. 2–4 hours to design, code, test. Includes documentation. |
| **Backward compatibility migration** | Data Load / Automation | M | If migrating existing users with only PRM_NetworkManagementQC to receive PRM_AllowCaseManagerOwnerChange, requires batch job or Flow. ~2–3 hours including testing. |
| **Testing (end-to-end flows)** | QA / Regression | M | Run through all 5 affected flows (Ancillary PSV, PSV QC, PAR, Recred, Committee) with a test user assigned the new perm set. ~3–4 hours including bug fixes if needed. |
| **Documentation** | Readme / Setup Guide | S | Write auto-assignment logic, manual assignment process, backward compatibility notes. ~1 hour. |

**Total Estimated Effort:** S + S + M + M + M + S = **~9–13 hours — L (4–8 hrs baseline + migration/testing overhead)**  
*AI-estimated — validate with team based on provisioning platform and existing user count.*

---

## Deployment Sequence

1. **Create** `PRM_AllowCaseManagerOwnerChange` permission set in the org
2. **Update** `PRM_NetworkManagementQC` to remove the custom permission entry
3. **Set up auto-assignment** automation (Flow, Apex, or provisioning integration)
4. **Migrate existing users** with appropriate roles to receive the new permission set
5. **Test end-to-end** with 5 affected flows
6. **Document** the process in setup guide
7. **Validate** no regressions in dependent flows

---

## References

- **Custom Permission Definition:** `force-app/main/default/customPermissions/PRM_RestrictUsertochangeCaseManagerOwner.customPermission-meta.xml`
- **Current Permission Set:** `force-app/main/default/permissionsets/PRM_NetworkManagementQC.permissionset-meta.xml`
- **Related Flows:**
  - `force-app/main/default/omniScripts/PRM_AncillaryReassessmentPSV_English_*.os-meta.xml`
  - `force-app/main/default/omniScripts/PRM_OffCycleQCReview_English_*.os-meta.xml`
  - `force-app/main/default/omniScripts/PRM_PractitionerParticipationForm_English_*.os-meta.xml`
  - `force-app/main/default/omniScripts/PRM_OffCycleCredentialing_English_*.os-meta.xml`
  - `force-app/main/default/omniScripts/PRM_ReviewHACAC_English_*.os-meta.xml`

---

## Sign-Off

- **Product Owner:** [TO BE ASSIGNED]
- **Technical Lead:** [TO BE ASSIGNED]
- **QA Lead:** [TO BE ASSIGNED]
