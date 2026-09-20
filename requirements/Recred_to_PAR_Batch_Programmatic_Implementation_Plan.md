# Recredentialing to PAR Case Manager – Batch/Programmatic Creation
## Step-by-Step Implementation Plan (Field-by-Field)

**Purpose:** Close Recredentialing case managers and create new PAR (Practitioner Participation Request) case managers for the same practitioners via batch/programmatic logic (no form).

**Constraint:** Cannot change record type on existing IndividualApplication. Must create a **new** IndividualApplication with RecordType `PRM_PractitionerParticipationRequest`.

**Reference DataRaptors / Patterns:**
- `PRMDRCreateCaseCaseManagerExistingNPI` – creates PAR case manager for existing practitioner (no new Account)
- `PRMDRCaseCaseManagerRecredTerminate` – closes Recred case manager
- `PRM_PractitionerActivationBatchHelper` – updates practitioner associations with new case manager
- `PRM_CaseManagerDenialUtility` – denial/closure logic for pending records

---

## 1. Source Data (From Recredentialing Case Manager)

Before processing, query the following from the Recred case manager and related records:

### 1.1 IndividualApplication (Recred Case Manager) – Fields to Read

| Field | API Name | Usage | Notes |
|-------|----------|-------|-------|
| Id | Id | Reference | Recred case manager to close |
| AccountId | AccountId | Practitioner Account Id | Same practitioner for new PAR |
| AppliedDate | AppliedDate | Optional copy | — |
| Category | Category | Copy | "Credentialing" |
| PRM_CorporateReceiptDate__c | PRM_CorporateReceiptDate__c | Optional copy | — |
| PRM_FHNaticCaseNumber__c | PRM_FHNaticCaseNumber__c | Optional copy | — |
| PRM_FormType__c | PRM_FormType__c | Optional copy | — |
| PRM_Stage__c | PRM_Stage__c | Closure | e.g. "Case Complete" or similar |
| Status | Status | Closure | "Pending Closure" or "Closed" |
| PRM_Decision_Date__c | PRM_Decision_Date__c | Closure | Date.today() |
| PRM_DenialReason__c | PRM_DenialReason__c | Closure | Reason for closing Recred |
| RecordType.DeveloperName | — | Verify | Must be `PRM_ReCredentialing` |

**Query:** Practitioner Account (`AccountId`) and `PersonContactId` via Account for Case creation.

### 1.2 Account (Practitioner) – Fields to Read

| Field | API Name | Usage |
|-------|----------|-------|
| Id | Id | Link new PAR Case Manager & Case |
| PersonContactId | PersonContactId | Case.ContactId |
| PRM_PNC__c | PRM_PNC__c | Preserve for PAR Case Type logic |
| RecordType.DeveloperName | — | Must be PRM_Practitioner |

---

## 2. Phase 1: Close Recredentialing Case Manager

### 2.1 IndividualApplication (Recred) – Fields to Update

| Field | API Name | Value | Notes |
|-------|----------|-------|-------|
| Status | Status | `"Pending Closure"` or `"Closed"` | Align with PAR Close Case behavior |
| PRM_Stage__c | PRM_Stage__c | `"Case Complete"` | Or business-defined closure stage |
| PRM_Decision_Date__c | PRM_Decision_Date__c | `Date.today()` | Closure date |
| PRM_DenialReason__c | PRM_DenialReason__c | `"Sanction Found"` | Use valid picklist value; "Recred to PAR Conversion" and "Business Decision" are not valid for Recred |

**Do not change:** RecordTypeId, AccountId, Id.

### 2.2 Case (Linked to Recred) – Fields to Update

| Field | API Name | Value |
|-------|----------|-------|
| Status | Status | `"Closed"` |
| PRM_DenialReason__c | PRM_DenialReason__c | Same as Case Manager |

**Query:** `SELECT Id, PRM_CaseManager__c FROM Case WHERE PRM_CaseManager__c = :recredCaseManagerId`

### 2.3 ContentNote (Optional)

Create a ContentNote on the Recred Case Manager for audit: e.g. "Closed for Recred to PAR Conversion – [Date]"

---

## 3. Phase 2: Create New PAR Case Manager and Case

**Logic pattern:** Use `PRMDRCreateCaseCaseManagerExistingNPI` pattern – practitioner exists, do NOT create new Account.

### 3.1 IndividualApplication (New PAR Case Manager) – Fields to Set

| Field | API Name | Value | Source |
|-------|----------|-------|--------|
| RecordTypeId | RecordTypeId | `PRM_PractitionerParticipationRequest` | `Schema.SObjectType.IndividualApplication.getRecordTypeInfosByDeveloperName().get('PRM_PractitionerParticipationRequest').getRecordTypeId()` |
| AccountId | AccountId | Practitioner Account Id | From Recred Case Manager |
| ApplicationType | ApplicationType | `"Individual"` | Default for PAR |
| AppliedDate | AppliedDate | `Datetime.now()` | — |
| Category | Category | `"Credentialing"` | — |
| PRM_Stage__c | PRM_Stage__c | `"Application Review"` | PAR entry stage |
| Status | Status | `"Submitted"` | PAR entry status |
| PRM_PNC__c | PRM_PNC__c | From practitioner Account | If practitioner is PNC |
| PRM_CorporateReceiptDate__c | PRM_CorporateReceiptDate__c | Optional | From Recred or null |
| PRM_FHNaticCaseNumber__c | PRM_FHNaticCaseNumber__c | Optional | From Recred or null |
| PRM_FormType__c | PRM_FormType__c | Optional | — |
| PRM_ExpeditedCred__c | PRM_ExpeditedCred__c | false | Default |
| PRM_PDMManualUpdateType__c | PRM_PDMManualUpdateType__c | `"Recred to PAR Conversion"` | Custom value – may need new picklist value |

**Note:** ApplicationCaseId will be set after Case is created (see below).

### 3.2 Case (New) – Fields to Set

| Field | API Name | Value | Notes |
|-------|----------|-------|-------|
| RecordTypeId | RecordTypeId | `PRM_PRM` | `Schema.SObjectType.Case.getRecordTypeInfosByDeveloperName().get('PRM_PRM').getRecordTypeId()` |
| AccountId | AccountId | Practitioner Account Id | Same as PAR Case Manager |
| ContactId | ContactId | Account.PersonContactId | Practitioner contact |
| Type | Type | `"Application Review"` or `"PNC"` if PNC | Based on PRM_PNC__c |
| Status | Status | `"New"` | — |
| Origin | Origin | `"Web"` or `"Recred to PAR Conversion"` | Configurable |
| PRM_CaseManager__c | PRM_CaseManager__c | **New PAR Case Manager Id** | Set after IndividualApplication insert |
| PRM_IsRoundRobinLogic__c | PRM_IsRoundRobinLogic__c | false | Default |

### 3.3 Creation Order

1. Insert **IndividualApplication** (PAR) – get Id
2. Insert **Case** – set `PRM_CaseManager__c` = new PAR Case Manager Id
3. Update **IndividualApplication** – set `ApplicationCaseId` = new Case Id

---

## 4. Phase 3: Create PRM_CaseDataManager__c (CDM)

The CDM is a header record that tracks which child data types are in scope for the case manager. PAR flows expect a CDM.

### 4.1 PRM_CaseDataManager__c – Fields to Set

| Field | API Name | Value | Notes |
|-------|----------|-------|-------|
| PRM_CaseManager__c | PRM_CaseManager__c | New PAR Case Manager Id | Required |
| PRM_PersonAccount__c | PRM_PersonAccount__c | true | Practitioner is in scope |
| PRM_Account__c | PRM_Account__c | false | Or true if Vendor data |
| PRM_HealthCareProvider__c | PRM_HealthCareProvider__c | true | Practitioner has HealthcareProvider |
| PRM_HealthCareProviderTaxonomy__c | PRM_HealthCareProviderTaxonomy__c | true | — |
| PRM_Identifier__c | PRM_Identifier__c | true | — |
| PRM_BoardCertification__c | PRM_BoardCertification__c | true | — |
| PRM_HealthCarePractitionerFacility__c | PRM_HealthCarePractitionerFacility__c | true | PPL data |
| PRM_HealthCareFacility__c | PRM_HealthCareFacility__c | true | Practice locations |
| PRM_HealthcareFacilityNetwork__c | PRM_HealthcareFacilityNetwork__c | true | — |
| PRM_HealthCareProviderNPI__c | PRM_HealthCareProviderNPI__c | true | — |
| PRM_Location__c | PRM_Location__c | true | — |
| PRM_Address__c | PRM_Address__c | true | — |
| PRM_AlternativeContactMethod__c | PRM_AlternativeContactMethod__c | true/false | Based on existing data |
| PRM_ProviderFeature__c | PRM_ProviderFeature__c | true/false | Based on existing data |
| PRM_AccountToAccountRelationship__c | PRM_AccountToAccountRelationship__c | true/false | If AAR used |

**Option A – Copy from Recred CDM:** Query existing `PRM_CaseDataManager__c` WHERE `PRM_CaseManager__c` = Recred Id, create new CDM with same flags, new `PRM_CaseManager__c` = PAR Id.

**Option B – Default all true:** Create CDM with all data-type flags = true (simplest; may include types not yet populated).

### 4.2 IndividualApplication Update (After CDM Insert)

| Field | API Name | Value |
|-------|----------|-------|
| PRM_CaseDataManager__c | PRM_CaseDataManager__c | New CDM Id |

**Trigger:** `PRM_CDMTriggerHandler.assignCDMOnCaseManager` populates this on CDM insert – may not need explicit update if CDM insert triggers it.

---

## 5. Phase 4: Update Practitioner Records and Associations

All practitioner-related records that were linked to the **Recred** case manager must be updated to reference the **new PAR** case manager where appropriate. The key field is `PRM_CaseManager__c` on many child objects.

### 5.1 Practitioner Account (Account)

| Field | API Name | Value | Notes |
|-------|----------|-------|-------|
| PRM_CaseManager__c | PRM_CaseManager__c | **New PAR Case Manager Id** | Points to active case manager |
| PRM_CredentialingStatus__c | PRM_CredentialingStatus__c | `"Credentialing In Progress"` | Reset for new PAR |
| PRM_Pending__c | PRM_Pending__c | true | PAR is in progress |

**Condition:** Account is the practitioner (AccountId from Recred). RecordType = PRM_Practitioner.

**Do NOT change:** PRM_PNC__c, PRM_DelegatedOnly__c unless business rules require.

### 5.2 Objects with PRM_CaseManager__c – Update to New PAR Case Manager

These objects link to a case manager. When moving from Recred to PAR, **decision required:**  
- **Option A (Recred-specific):** Leave existing records linked to Recred (closed). Create **new** pending copies for PAR.  
- **Option B (Repoint):** Update `PRM_CaseManager__c` from Recred Id to PAR Id on existing records.

**Recommendation for batch:** **Option B – Repoint** existing practitioner data to the new PAR case manager, so the same practice locations, NPIs, etc. flow through the PAR process. This matches the idea of "taking them through PAR again" using existing data.

#### 5.2.1 HealthcareProviderNpi

| Field | API Name | Value |
|-------|----------|-------|
| PRM_CaseManager__c | PRM_CaseManager__c | New PAR Case Manager Id |
| PRM_Pending__c | PRM_Pending__c | true (if repointing for PAR) |

**Query:** `WHERE PractitionerId = :personContactId` (from practitioner Account).

#### 5.2.2 Identifier

| Field | API Name | Value |
|-------|----------|-------|
| PRM_CaseManager__c | PRM_CaseManager__c | New PAR Case Manager Id |
| PRM_Pending__c | PRM_Pending__c | true |

**Query:** `WHERE ParentRecordId = :practitionerAccountId`.

#### 5.2.3 HealthcareProvider

| Field | API Name | Value |
|-------|----------|-------|
| PRM_CaseManager__c | PRM_CaseManager__c | New PAR Case Manager Id |
| PRM_Pending__c | PRM_Pending__c | true |

**Query:** `WHERE AccountId = :practitionerAccountId`.

#### 5.2.4 HealthcareProviderTaxonomy

| Field | API Name | Value |
|-------|----------|-------|
| PRM_CaseManager__c | PRM_CaseManager__c | New PAR Case Manager Id |
| PRM_Pending__c | PRM_Pending__c | true |

**Query:** `WHERE PractitionerId = :personContactId`.

#### 5.2.5 BoardCertification

| Field | API Name | Value |
|-------|----------|-------|
| PRM_CaseManager__c | PRM_CaseManager__c | New PAR Case Manager Id |
| PRM_Pending__c | PRM_Pending__c | true |

**Query:** `WHERE PractitionerId = :personContactId`.

#### 5.2.6 HealthcarePractitionerFacility (PPL)

| Field | API Name | Value |
|-------|----------|-------|
| PRM_CaseManager__c | PRM_CaseManager__c | New PAR Case Manager Id |
| PRM_Pending__c | PRM_Pending__c | true |

**Query:** Via Recred Case Manager's PPLs, or by PractitionerId + AccountId (vendor).

#### 5.2.7 HealthcareFacility (Practice Location)

| Field | API Name | Value |
|-------|----------|-------|
| PRM_CaseManager__c | PRM_CaseManager__c | New PAR Case Manager Id |
| PRM_Pending__c | PRM_Pending__c | true |

**Query:** Practice locations linked to Recred's PPLs or via AccountId.

**Note:** Per `PRM_RemoveParPncCaseManagerExecutor`, HealthcareFacility should **not** have `PRM_CaseManager__c` pointing to Par Form in some flows. Verify: for **batch-created PAR**, practice locations typically do have a case manager link during credentialing. Confirm with business.

#### 5.2.8 HealthcareFacilityNetwork

| Field | API Name | Value |
|-------|----------|-------|
| PRM_CaseManager__c | PRM_CaseManager__c | New PAR Case Manager Id |
| PRM_Pending__c | PRM_Pending__c | true |

#### 5.2.9 Location (Schema.Location)

| Field | API Name | Value |
|-------|----------|-------|
| PRM_CaseManager__c | PRM_CaseManager__c | New PAR Case Manager Id |
| PRM_Pending__c | PRM_Pending__c | true |

**Query:** HealthcareFacility.LocationId from practitioner's facilities (see 5.2.6–5.2.7). **Required** for Application Review to filter locations correctly (prevents "all locations from group" showing as additional locations).

#### 5.2.10 Address (Schema.Address)

| Field | API Name | Value |
|-------|----------|-------|
| PRM_CaseManager__c | PRM_CaseManager__c | New PAR Case Manager Id |

**Query:** `WHERE PRM_CaseManager__c = :recredId`

#### 5.2.11 PRM_ProviderFeature__c

| Field | API Name | Value |
|-------|----------|-------|
| PRM_CaseManager__c | PRM_CaseManager__c | New PAR Case Manager Id |
| PRM_Pending__c | PRM_Pending__c | true |

**Query:** `WHERE PRM_Practitioner__c = :personContactId`.

#### 5.2.12 PRM_ContactMethod__c

| Field | API Name | Value |
|-------|----------|-------|
| PRM_CaseManager__c | PRM_CaseManager__c | New PAR Case Manager Id (if field exists) |
| PRM_Pending__c | PRM_Pending__c | true |

**Query:** Via HealthcareFacility.

#### 5.2.13 Vendor Accounts (if in scope)

| Field | API Name | Value |
|-------|----------|-------|
| PRM_CaseManager__c | PRM_CaseManager__c | New PAR Case Manager Id |

**Query:** Vendor accounts linked to practitioner's practice locations.

### 5.3 Update Order / Considerations

1. **Dependency:** Many child records are linked via practitioner (Account/Contact) or via Recred case manager. Query scope:
   - By Recred `PRM_CaseManager__c` = Recred Id
   - By Practitioner AccountId / PersonContactId

2. **Transactional integrity:** Run in a single transaction per practitioner, or use a batch with commit per practitioner.

3. **Governor limits:** For practitioners with many PPLs, NPIs, taxonomies, etc., consider:
   - Batch size
   - Async (Queueable/ Batch) if record count is high

---

## 6. Phase 5: Additional Considerations

### 6.1 PDMManualUpdateType Picklist

Add picklist value `"Recred to PAR Conversion"` to `PRM_PDMManualUpdateType__c` on IndividualApplication if not present.

### 6.2 Case Assignment / Owner

Determine Case Owner (user or queue). Existing logic may use round-robin. For batch, consider:
- Same owner as Recred Case
- Specific queue (e.g. "Application Review")

### 6.3 ContentNote / Audit

Create ContentNote on new PAR Case Manager: "Created from Recred to PAR Conversion – Source Recred Case Manager: [Recred Id]"

### 6.4 Exclusion Logic

Do **not** convert Recred case managers that:
- Are already Closed / Pending Closure
- Have no valid practitioner Account
- Practitioner Account is inactive or terminated
- Business-defined exclusion rules

### 6.5 Rollback Strategy

If creation fails mid-process:
- Recred may already be closed
- PAR Case Manager / Case may be created
- Practitioner associations may be partially updated  
Define rollback rules (e.g., reopen Recred, delete PAR, revert associations) or run in a sandbox first.

---

## 7. Summary Table – All Objects Touched

| # | Object | Action | Key Fields |
|---|--------|--------|------------|
| 1 | IndividualApplication (Recred) | UPDATE | Status, PRM_Stage__c, PRM_Decision_Date__c, PRM_DenialReason__c |
| 2 | Case (Recred) | UPDATE | Status = Closed, PRM_DenialReason__c |
| 3 | IndividualApplication (PAR) | INSERT | RecordTypeId, AccountId, Status, PRM_Stage__c, etc. |
| 4 | Case (PAR) | INSERT | AccountId, ContactId, Type, PRM_CaseManager__c |
| 5 | IndividualApplication (PAR) | UPDATE | ApplicationCaseId |
| 6 | PRM_CaseDataManager__c | INSERT | PRM_CaseManager__c = PAR Id, data flags |
| 7 | IndividualApplication (PAR) | UPDATE | PRM_CaseDataManager__c (may auto from trigger) |
| 8 | Account (Practitioner) | UPDATE | PRM_CaseManager__c, PRM_CredentialingStatus__c, PRM_Pending__c |
| 9 | HealthcareProviderNpi | UPDATE | PRM_CaseManager__c, PRM_Pending__c |
| 10 | Identifier | UPDATE | PRM_CaseManager__c, PRM_Pending__c |
| 11 | HealthcareProvider | UPDATE | PRM_CaseManager__c, PRM_Pending__c |
| 12 | HealthcareProviderTaxonomy | UPDATE | PRM_CaseManager__c, PRM_Pending__c |
| 13 | BoardCertification | UPDATE | PRM_CaseManager__c, PRM_Pending__c |
| 14 | HealthcarePractitionerFacility | UPDATE | PRM_CaseManager__c, PRM_Pending__c |
| 15 | HealthcareFacility | UPDATE | PRM_CaseManager__c, PRM_Pending__c |
| 16 | Location (Schema.Location) | UPDATE | PRM_CaseManager__c, PRM_Pending__c |
| 17 | HealthcareFacilityNetwork | UPDATE | PRM_CaseManager__c, PRM_Pending__c |
| 18 | Address | UPDATE | PRM_CaseManager__c |
| 19 | PRM_ProviderFeature__c | UPDATE | PRM_CaseManager__c, PRM_Pending__c |
| 20 | Account (Vendor) | UPDATE | PRM_CaseManager__c (if applicable) |

---

## 8. Open Questions for Business / Technical Review

1. **Repoint vs. clone:** Should existing practitioner data (PPL, NPI, taxonomy, etc.) be repointed to the new PAR case manager, or should new pending copies be created?
2. **HealthcareFacility.PRM_CaseManager__c:** Confirm whether practice locations should link to PAR case manager (some logic excludes Par Form from HCF links).
3. **Case Type:** Application Review vs. PNC – use Account.PRM_PNC__c to decide.
4. **Bulk vs. selective:** Which Recred case managers qualify? (e.g., specific stages, statuses, date ranges)
5. **CDM copy:** Copy flags from Recred CDM vs. default all true?
6. **Round-robin:** Should Case Owner follow existing assignment rules?

---

## 9. Next Steps

1. Review and approve this plan with business.
2. Add `PRM_PDMManualUpdateType__c` picklist value if needed.
3. Implement Apex batch/script following this field-by-field spec.
4. Test in sandbox with a small set of Recred case managers.
5. Validate downstream flows (Application Review, PSV, QC) work with batch-created PAR.
