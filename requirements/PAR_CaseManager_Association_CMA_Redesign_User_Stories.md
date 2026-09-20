# PAR Case Manager Association via PRM_CaseManagerAssociation__c
## Redesigned Architecture, Root Cause, Business Questions and Detailed User Stories

Document Version: 2.0
Created Date: April 29, 2026
Supersedes: PAR_CaseManager_Association_Stable_Link_User_Stories.md (v1.0 — new field approach)
Architecture Decision: Reuse PRM_CaseManagerAssociation__c junction object with PRM_HealthcarePractitionerFacility__c lookup instead of adding a new field on HCPF
Vertical: Provider Network Management (PNM)
Related Documents:
- PAR_AppReview_TerminatedLocation_InFlight_BugFix.md (US4)
- PAR_AppReview_TerminatedLocation_DailyScript_Analysis.md (US5)
- PAR_DeniedTerminated_RecordReuse_User_Stories.md (US1-US3)

---

## 1. What PRM_CaseManagerAssociation__c Is and How It Works

### Object Purpose

PRM_CaseManagerAssociation__c is a junction object described as:
"Junction object used to track and link Records created or updated as part of a guided flow to Case Managers"

It is a MASTER-DETAIL child of IndividualApplication via PRM_CaseManager__c.
Every record has exactly one parent IndividualApplication (the "Case Manager").
Each record has at most ONE populated lookup field pointing to the related Salesforce record.

### Key Fields

Field API Name | Label | Type | Notes
PRM_CaseManager__c | Parent Case Manager | MasterDetail to IndividualApplication | Primary parent - controls sharing
PRM_HealthcarePractitionerFacility__c | Related Practitioner Practice Location | Lookup to HealthcarePractitionerFacility | THE field we will use - deleteConstraint = SetNull
PRM_HealthcareFacility__c | Related Practice Location | Lookup to HealthcareFacility | Used by PDM and ancillary flows
PRM_Account__c | Related Account | Lookup to Account | —
PRM_Address__c | Related Address | Lookup to Address | —
PRM_HealthcareFacilityNetwork__c | Related Practice Location Summary | Lookup to HealthcareFacilityNetwork | —
PRM_HealthcareFacilityAssociation__c | Related Practice Location Association | Lookup to PRM_HealthcareFacilityAssociation__c | —
PRM_HealthcareProviderTaxonomy__c | Related Healthcare Provider Taxonomy | Lookup to HealthcareProviderTaxonomy | —
PRM_Identifier__c | Related Identifier | Lookup to Identifier | —
PRM_ProgramParticipation__c | Related Program Participation | Lookup to PRM_ProgramParticipation__c | —
PRM_ProviderFeature__c | Related Provider Feature | Lookup to PRM_ProviderFeature__c | —
PRM_BusinessLicense__c | Related Business License | Lookup to BusinessLicense | —
PRM_RequestType__c | Request Type | Text(255) | —

### Relevant Record Type

RecordType DeveloperName | Label | Used For
Practitioner_Practice_Location | Practitioner Practice Location | CMA record linking a PAR case (IndividualApplication) to its HCPF record

### Relationship Diagram

Case
  PRM_CaseManager__c (lookup on Case to IndividualApplication)
    IndividualApplication (the "PAR Case Manager")
      PRM_UseCaseManagerAssociation__c = true  (flag set after CMA records are inserted)
        PRM_CaseManagerAssociation__c (master-detail child, RecordType = Practitioner_Practice_Location)
          PRM_CaseManager__c = IndividualApplication.Id  (master-detail parent)
          PRM_HealthcarePractitionerFacility__c = HCPF.Id  (the affiliation record)

### Who Currently Creates CMA Records (and Who Does NOT)

CREATES CMA:
- PDM Manual Update flow: PRM_PDMRecordsCreation_Procedure_15 calls remote method createCaseManagerAssociation
  which invokes PRM_CaseManagerAssociationService.cls + PRM_CaseManagerAssociationDirectBuilder.cls
  createCMAForPractitionerPracticeLocation() - sets PRM_HealthcarePractitionerFacility__c
- Ancillary form flow: PRM_AncillaryFormRecordsCreation_Procedure_18 calls PRMDRPCreateCaseManagerAssociation
- Backfill batch: PRM_CaseManagerAssociationBatch for historical PDM IndividualApplications

DOES NOT CREATE CMA:
- PAR form submission (PRM_CreateParFormRecords, PRM_CreatePractitionerAddressRecords, PRM_PractitionerAddressCreation) - confirmed by full search, zero CMA references in any version of these IPs
- PRMDRCreateHealthcarePractitionerFacility - creates HCPF only, no CMA

KEY INSIGHT: CMA records for HCPF already exist for PDM-originated cases.
The gap is that the PAR form submission does NOT create them.
This is the new behavior we need to add.

### Who Currently Reads CMA Records

Reader | What It Reads | Gate Condition
PRMDRExtractCaseManagerAssociationDetails (DR Extract) | All lookup fields from CMA by CaseManagerId | IndividualApplication.PRM_UseCaseManagerAssociation__c = true
PRMDRECaseManagerAssocFacility (DR Extract) | CMA HealthcareFacility details by CaseManagerId | active=false (legacy)
PRM_FetchCaseRelatedDetails_Procedure_6 (IP) | Calls PRMDRExtractCaseManagerAssociationDetails | Gates on UseCaseManagerAssociation flag AND PDM update type
PRM_CaseManagerRelatedListController.cls (Apex) | All CMA fields for UI display | By CaseManagerId (no gate)

### The IndividualApplication.PRM_UseCaseManagerAssociation__c Flag

This boolean field is set to true by PRM_CaseManagerAssociationService after inserting CMA records.
Downstream IPs check this flag before executing CMA DR queries (avoids unnecessary queries when CMA records dont exist).
For PAR cases, this flag is currently always false because CMA records are never created for PAR submissions.
After our change: PAR form submission will set this flag to true.

---

## 2. The Problem: How PRM_CaseManager__c Gets Overwritten

### The Failure Chain (unchanged from v1.0 analysis)

[PAR Form Submit]
  PRMDRCreateHealthcarePractitionerFacility
    HCPF.PRM_CaseManager__c = IA-PAR-001
    HCPF.PRM_Pending__c = true
    CMA record: NOT CREATED (gap)

[PDM / Provider Change Termination runs on same Practice Location]
  PRMDRLoadUpdateHCPF (via PRM_PDMRecordsCreationLMSPlus)
    HCPF.PRM_CaseManager__c = IA-PDM-002  <-- OVERWRITES PAR LINK

  PRM_ProvChangeTerminationBatch (Apex via PRM_PracLocTermHelper.cls lines 264-299)
    HCPF.PRM_CaseManager__c = IA-PCR-003  <-- OVERWRITES PAR LINK

[Any Review Flow Opens for PAR case]
  PRMExtractCaseDetails
    Case.PRM_CaseManager__c = IA-PAR-001  (Case still correctly points to PAR)
    CaseManagerId = IA-PAR-001

  PRMDRGetPractionerPracticeLocation / PRMExtractPracticeLocationToPractitionerFacility
    WHERE HCPF.PRM_CaseManager__c = 'IA-PAR-001'
    Returns: ZERO ROWS  <-- HCPF now holds IA-PDM-002 or IA-PCR-003

  PRMDREGetPracticeLocation EligibleForUpdate COUNTQUERY
    Finds HCPF via HealthcareFacilityId
    PRM_Active__c = false, PRM_Pending__c = true --> FALSE POSITIVE
    PRMDRPPractitionerDataUpdate fires --> REQUIRED FIELDS MISSING ERROR

### Why CMA Solves This

The CMA record is a CHILD of IndividualApplication (master-detail).
CMA.PRM_CaseManager__c = IA-PAR-001 (the PAR case) -- this NEVER changes.
CMA.PRM_HealthcarePractitionerFacility__c = HCPF.Id

When PDM overwrites HCPF.PRM_CaseManager__c to IA-PDM-002,
the CMA record is completely unaffected. It still has:
  CMA.PRM_CaseManager__c = IA-PAR-001
  CMA.PRM_HealthcarePractitionerFacility__c = HCPF.Id

Review flows can now query:
  SELECT PRM_HealthcarePractitionerFacility__c
  FROM PRM_CaseManagerAssociation__c
  WHERE PRM_CaseManager__c = 'IA-PAR-001'
  AND RecordType.DeveloperName = 'Practitioner_Practice_Location'

And get the correct HCPF Ids regardless of what PDM did to HCPF.PRM_CaseManager__c.

---

## 3. Architectural Redesign

### What Changes in the Architecture

Step | Old Approach | New Approach
PAR form HCPF creation | Creates HCPF, stamps PRM_CaseManager__c on HCPF | Creates HCPF (unchanged) + creates CMA record (Practitioner_Practice_Location) linking PAR IndividualApplication to HCPF
PAR form HCPF reuse (denied/terminated) | Updates HCPF.PRM_CaseManager__c | Updates HCPF (unchanged) + creates/updates CMA record for new PAR case
IndividualApplication flag | PRM_UseCaseManagerAssociation__c = false (never set) | PRM_UseCaseManagerAssociation__c = true after CMA records inserted
Review flow HCPF lookup | DR queries HCPF WHERE PRM_CaseManager__c = CaseManagerId | DR queries CMA WHERE PRM_CaseManager__c = CaseManagerId AND RecordType = Practitioner_Practice_Location, then uses PRM_HealthcarePractitionerFacility__c as the HCPF Id
Terminated location detection | Not implemented (the bug) | CMA provides stable HCPF list; check HealthcareFacility.PRM_Active__c via HCPF.HealthcareFacilityId
Step 1 warning | Not implemented | New DR on first step of each review flow

### What Does NOT Change

Component | Why Not Changed
HCPF.PRM_CaseManager__c field | PDM and PCR flows continue writing to it - operational behavior unchanged
PRMDRLoadUpdateHCPF | Continues writing PDM CaseManager to HCPF - no change
PRM_PracLocTermHelper.cls (lines 264-299) | Provider Change termination batch unchanged
Existing CMA creation for PDM flows | PDM already creates CMA records - those paths are untouched
PRMDRECaseManagerAssocFacility (inactive DR) | Already reads CMA by CaseManagerId - can be re-activated and extended
HCPF creation logic (PRMDRCreateHealthcarePractitionerFacility) | Unchanged - CMA creation is a NEW parallel step

### SOQL Join Pattern for Review Flows (New Pattern)

Two-step lookup:

Step 1: Get HCPF Ids from CMA (stable, never overwritten)
  SELECT PRM_HealthcarePractitionerFacility__c,
         PRM_HealthcarePractitionerFacility__r.HealthcareFacilityId,
         PRM_HealthcarePractitionerFacility__r.HealthcareFacility.PRM_Active__c,
         PRM_HealthcarePractitionerFacility__r.HealthcareFacility.Name,
         PRM_HealthcarePractitionerFacility__r.HealthcareFacility.PRM_TerminationDate__c
  FROM PRM_CaseManagerAssociation__c
  WHERE PRM_CaseManager__c = :CaseManagerId
  AND RecordType.DeveloperName = 'Practitioner_Practice_Location'
  AND PRM_HealthcarePractitionerFacility__c != null

Step 2: Use the HCPF Ids or HealthcareFacilityIds for downstream queries

Terminated location detection (from the same query):
  If PRM_HealthcarePractitionerFacility__r.HealthcareFacility.PRM_Active__c = false
  then that location was terminated after PAR submission

---

## 4. Business Questions

### Category A - UX for Terminated Location Warning

Q# | Question | Why It Matters
A1 | When the terminated location warning is shown on Step 1, "Update Locations" -- where does it navigate? (a) Inline location picker within the review flow, (b) PAR form in edit mode (requires post-submission editability feature from ParticipationFormEnhancements), (c) Task created for data entry team. Which is expected? | Determines implementation complexity and dependencies.
A2 | "Close Case" -- does this mean (a) close only the IndividualApplication, (b) close the Salesforce Case record with reason "Practice Location Terminated", or (c) mark HCPF records IsActive=false + PRM_Pending__c=false? | Determines the close action scope.
A3 | Hard block or soft warning? Business answer says "go back or close" which implies hard block. Confirm: can the specialist NOT proceed past Step 1 until they choose Update or Close? | Core UX decision.
A4 | If a case has 3 locations and 1 is terminated: must user address the terminated one before proceeding, or can they remove it and continue with the other 2? | Multi-location handling.
A5 | At the PDA stage, if a location is still terminated when PDA opens: is that a hard block or can PDA activate with the remaining active locations? | PDA-specific path decision.

### Category B - CMA Record Lifecycle for PAR

Q# | Question | Why It Matters
B1 | When a PAR case is DENIED and closed: should the CMA records for that case be deleted, or left in place (as a historical record)? Since CMA is master-detail to IndividualApplication, closing the IA does not auto-delete CMA -- explicit deletion needs to be built if required. | Data hygiene decision. - we can leave it as is for now
B2 | When a PAR is denied and re-submitted (US1 reuse scenario): should the NEW PAR case get a NEW CMA record pointing to the same HCPF? Or should we update the existing CMA record's PRM_CaseManager__c to the new PAR case Id? (Note: PRM_CaseManager__c is a master-detail field -- it CANNOT be updated after creation. So the answer must be: create a NEW CMA record for the new PAR case.) | Master-detail constraint drives this decision - confirm business expectation. - new CMA should be created for every case manager
B3 | IndividualApplication.PRM_UseCaseManagerAssociation__c will be set to true when PAR form creates CMA records. Are there any existing flows that check this flag and might behave differently for PAR cases once it is true? Specifically: PRM_FetchCaseRelatedDetails_Procedure_6 gates CMA reads on this flag AND on PDM update type. Should PAR cases have their own gate condition? | Risk of unintended side effects from setting the flag.
B4 | Should the CMA record for the PAR-HCPF link use PRM_RequestType__c to distinguish it from PDM-created CMA records? For example: PRM_RequestType__c = 'PAR' for PAR-created records vs no value for PDM-created records. | Helps differentiate PAR CMA records from PDM CMA records in queries and reports.

### Category C - Data Migration

Q# | Question | Why It Matters
C1 | For existing in-flight PAR cases (HCPF.PRM_Pending__c = true, no CMA records exist): should we run a one-time migration to CREATE CMA records for those cases? Without migration, the terminated-location warning on Step 1 will not work for existing cases. | Migration is required for existing in-flight PAR cases.
C2 | For cases where PDM has already overwritten HCPF.PRM_CaseManager__c: the original PAR IndividualApplication Id is still on Case.PRM_CaseManager__c. Can we use Case.PRM_CaseManager__c to recover the PAR case Id and create the retroactive CMA records? | Recovery strategy for already-broken existing cases.
C3 | What is the count of currently in-flight PAR cases (HCPF.PRM_Pending__c = true) in production? | Sizes the migration effort.
C4 | The PRMDRPCreateCaseManagerAssociation DataRaptor is currently active=false (disabled). Is this the intended long-term state or can it be re-activated and extended to also handle PAR CMA creation? | Determines whether to extend the existing inactive DR or build a new path.

### Category D - Review Flow Behavior

Q# | Question | Why It Matters
D1 | For PSV, QC, PDA, and Network Management QC: does the terminated-location check also need to fire on Step 1 of each of these flows, or only App Review? Business said App Review / PSV / QC -- confirm PDA and Network Management QC are also in scope. | Scope of the warning across all 5 flows.
D2 | When a case is in PSV or QC review and the specialist sees the terminated location warning: should "Close Case" be available at PSV/QC stage, or is closing only valid at App Review? | Action options differ by review stage.

---

## 5. User Stories

---

### USER STORY 6 (Revised): Create PRM_CaseManagerAssociation__c Records During PAR Form Submission

Story Number: US6
Priority: P0 -- Foundation for all subsequent stories
Persona: Developer
Component Type: Integration Procedure + DataRaptor creation + Apex service extension
Epic: PAR Case Manager Association via CMA Object
Depends On: None
Blocks: US7, US8, US9, US10, US11, US12

#### Story

As a developer building the PAR credentialing workflow,
I want the PAR form submission flow to create a PRM_CaseManagerAssociation__c record
(RecordType = Practitioner_Practice_Location) linking the PAR IndividualApplication
to each HealthcarePractitionerFacility record it creates or reuses,
So that a stable, immutable, case-owned link between the PAR case and its HCPF records
exists regardless of any subsequent PDM or Provider Change termination that overwrites
HCPF.PRM_CaseManager__c.

#### Why It Matters

PRM_CaseManagerAssociation__c is a master-detail child of IndividualApplication.
Once created with PRM_CaseManager__c = PAR IndividualApp Id, this record CANNOT have
its parent changed. PDM and Provider Change termination flows write to
HCPF.PRM_CaseManager__c directly -- they have no awareness of CMA records and do not
touch them. This makes the CMA record an immutable, reliable link from the PAR case
to its HCPF records.

The PAR form currently creates HCPF records via PRMDRCreateHealthcarePractitionerFacility
and PRMUpdatePracticeToPractitioner, but creates NO CMA records. This is the gap.

#### How CMA Is Already Created in the Codebase (Pattern to Follow)

The PDM flow uses:
  PRM_PDMRecordsCreation_Procedure_15
    --> remote method: createCaseManagerAssociation
    --> PRM_PDMManualUtility.cls dispatches to PRM_CaseManagerAssociationService.cls
    --> PRM_CaseManagerAssociationService.createCaseManagerAssociation()
          calls PRM_CaseManagerAssociationDirectBuilder.createCMAForPractitionerPracticeLocation()
          builds CMA with:
            PRM_CaseManager__c = IndividualApplicationId (the PAR case Id)
            PRM_HealthcarePractitionerFacility__c = HCPF.Id
            RecordType = Practitioner_Practice_Location
          inserts records
          sets IndividualApplication.PRM_UseCaseManagerAssociation__c = true

For PAR, we will follow the same Apex path (PRM_CaseManagerAssociationService) to reuse
the existing tested code.

#### Scope of Changes

Component | Type | Change
PRM_CreatePractitionerAddressRecords (IP, v41 latest) | IP - add new step | After the HCPF creation/update DR steps succeed, add a new Remote Action step: call PRM_CaseManagerAssociationService.createCMAsForPARHCPF() with the list of newly created/updated HCPF Ids and the PAR IndividualApplicationId
PRM_PractitionerAddressCreation (IP, v3 latest) | IP - add new step | Same: add Remote Action to create CMA records after HCPF steps complete
PRM_CaseManagerAssociationService.cls | Apex - new method | Add createCMAsForPARHCPF(List<Id> hcpfIds, Id indivAppId) method: iterates hcpfIds, calls createCMAForPractitionerPracticeLocation() for each, sets PRM_UseCaseManagerAssociation__c = true on the IndividualApplication. Uses existing PRM_CaseManagerAssociationDirectBuilder internally.
PRM_CaseManagerAssociationDirectBuilder.cls | Apex - confirm reuse or extend | Confirm createCMAForPractitionerPracticeLocation() correctly sets RecordType = Practitioner_Practice_Location, PRM_CaseManager__c, and PRM_HealthcarePractitionerFacility__c. Add PRM_RequestType__c = 'PAR' to distinguish PAR-created CMA records from PDM-created ones (pending business answer to Question B4).
New Data Migration Batch: PRM_PARCMABackfillBatch.cls | Apex batch (new) | For existing in-flight PAR cases: query HCPF WHERE PRM_Pending__c = true AND related IndividualApplication RecordType = PRM_PractitionerParticipationRequest AND no CMA record exists. Create CMA records for each. Set PRM_UseCaseManagerAssociation__c = true on the IndividualApplication. Produce run report.

#### CMA Record Structure for PAR

PRM_CaseManagerAssociation__c record per HCPF:
  PRM_CaseManager__c = PAR IndividualApplication Id (master-detail parent - IMMUTABLE after creation)
  PRM_HealthcarePractitionerFacility__c = HCPF.Id
  RecordType.DeveloperName = Practitioner_Practice_Location
  PRM_RequestType__c = 'PAR' (proposed - confirm with business per Question B4)
  All other lookup fields = null

On the PAR IndividualApplication:
  PRM_UseCaseManagerAssociation__c = true (set after CMA records inserted)

#### Acceptance Criteria

Scenario 1 -- PAR form submission creates CMA records for new HCPF

Given a user submits a new PAR form with 2 practice locations,
When PRMDRCreateHealthcarePractitionerFacility runs and creates 2 HCPF records,
Then the new IP step triggers createCMAsForPARHCPF() with those 2 HCPF Ids,
AND 2 PRM_CaseManagerAssociation__c records are created:
  Each has PRM_CaseManager__c = PAR IndividualApplication Id
  Each has PRM_HealthcarePractitionerFacility__c = the respective HCPF Id
  Each has RecordType = Practitioner_Practice_Location,
AND the PAR IndividualApplication.PRM_UseCaseManagerAssociation__c = true.

---

Scenario 2 -- PAR form reuse (denied/terminated HCPF) creates new CMA for new PAR case

Given a practitioner re-submits a PAR and PRMUpdatePracticeToPractitioner reuses an existing HCPF (HCPF.Id = existing),
When the IP runs,
Then a NEW CMA record is created for the NEW PAR IndividualApplication:
  PRM_CaseManager__c = NEW PAR IndividualApplication Id
  PRM_HealthcarePractitionerFacility__c = existing HCPF.Id
  RecordType = Practitioner_Practice_Location,
AND any prior CMA records for the SAME HCPF from the DENIED PAR case remain (historical record - per business decision on Question B1),
AND the new PAR IndividualApplication.PRM_UseCaseManagerAssociation__c = true.

---

Scenario 3 -- PDM termination does not affect PAR CMA records

Given a PAR case has CMA records created per Scenario 1,
When PRMDRLoadUpdateHCPF runs (PDM termination) and overwrites HCPF.PRM_CaseManager__c = PDM case Id,
Then the CMA records for the PAR case are completely unaffected (master-detail to PAR IndividualApplication, not to HCPF),
AND querying CMA WHERE PRM_CaseManager__c = PAR IndividualApp Id still returns the correct HCPF Ids.

---

Scenario 4 -- Provider Change termination batch does not affect PAR CMA records

Given a PAR case has CMA records, and PRM_ProvChangeTerminationBatch runs and overwrites HCPF.PRM_CaseManager__c,
Then the CMA records for the PAR case are unaffected (same reason as Scenario 3).

---

Scenario 5 -- Data migration creates CMA records for existing in-flight PAR cases

Given existing in-flight PAR HCPF records (PRM_Pending__c = true) with no corresponding CMA,
When PRM_PARCMABackfillBatch runs,
Then CMA records are created for each HCPF linked to a PAR IndividualApplication,
AND PRM_UseCaseManagerAssociation__c = true is set on each PAR IndividualApplication,
AND a migration report is produced: records processed / CMA created / errors.

---

Scenario 6 -- No duplicate CMA records created on re-run

Given a PAR case that already has CMA records (Scenario 1 completed),
When the PAR form submission IP runs again (e.g., retry),
Then createCMAsForPARHCPF() checks for existing CMA records before inserting
(same deduplication pattern as PRM_PDMManualCrossRefFinishService.filterExistingCaseManagerAssociations()),
AND no duplicate CMA records are created.

#### Estimated Effort

Component | Effort | Notes
New method PRM_CaseManagerAssociationService.createCMAsForPARHCPF() | S | Reuses existing builder and insert logic; add deduplication check
Confirm PRM_CaseManagerAssociationDirectBuilder reuse | XS | Read and confirm - likely no change
Update PRM_CreatePractitionerAddressRecords v41 - add Remote Action step | S | Add one step after HCPF creation DR steps
Update PRM_PractitionerAddressCreation v3 - add Remote Action step | S | Same pattern
PRM_PARCMABackfillBatch - new Apex batch | M | Query in-flight PAR HCPF records + CMA creation + flag setting + report
Unit tests | M | New method tests + batch tests
Regression testing | M | PAR form + PDM termination + Provider Change - confirm CMA not affected
TOTAL | M-L |

---

### USER STORY 7 (Revised): Update All Review Flow HCPF-Loading DataRaptors to Query via CMA

Story Number: US7
Priority: P0 -- Enables stable HCPF record retrieval across all review flows
Persona: Developer
Component Type: DataRaptor updates + Integration Procedure updates
Epic: PAR Case Manager Association via CMA Object
Depends On: US6 (CMA records must exist for PAR cases)
Blocks: US8, US9, US10, US11, US12

#### Story

As a developer,
I want all review flow DataRaptors that currently query HealthcarePractitionerFacility
directly by PRM_CaseManager__c to instead resolve HCPF Ids via
PRM_CaseManagerAssociation__c (WHERE PRM_CaseManager__c = PAR CaseManager Id
AND RecordType = Practitioner_Practice_Location),
So that HCPF records for a PAR case are reliably retrieved regardless of whether
PDM or Provider Change termination has since overwritten HCPF.PRM_CaseManager__c.

#### New HCPF Lookup Pattern (All Review Flows)

Current pattern (broken when PDM overwrites HCPF.PRM_CaseManager__c):
  SELECT Id, HealthcareFacilityId, ...
  FROM HealthcarePractitionerFacility
  WHERE PRM_CaseManager__c = :CaseManagerId

New pattern (stable via CMA junction):
  Step A: Resolve HCPF Ids from CMA
    SELECT PRM_HealthcarePractitionerFacility__c,
           PRM_HealthcarePractitionerFacility__r.Id,
           PRM_HealthcarePractitionerFacility__r.HealthcareFacilityId,
           PRM_HealthcarePractitionerFacility__r.HealthcareFacility.PRM_Active__c,
           PRM_HealthcarePractitionerFacility__r.HealthcareFacility.Name,
           PRM_HealthcarePractitionerFacility__r.HealthcareFacility.BillingStreet,
           PRM_HealthcarePractitionerFacility__r.HealthcareFacility.BillingCity,
           PRM_HealthcarePractitionerFacility__r.HealthcareFacility.BillingState,
           PRM_HealthcarePractitionerFacility__r.HealthcareFacility.PRM_TerminationDate__c
    FROM PRM_CaseManagerAssociation__c
    WHERE PRM_CaseManager__c = :CaseManagerId
    AND RecordType.DeveloperName = 'Practitioner_Practice_Location'
    AND PRM_HealthcarePractitionerFacility__c != null

  Step B: Use HCPF Ids for the main HCPF DR query (pass as input list)
    OR: Use relationship traversal directly from CMA in a single DR

#### New DataRaptor: PRMDREGetPARCaseHCPFViaCMA

Type: DataRaptor Extract (new)
Purpose: Single DR that replaces the CaseManager-filtered HCPF queries in all review flows.
Input: CaseManagerId (PAR IndividualApplication Id)

Query on PRM_CaseManagerAssociation__c:
  WHERE PRM_CaseManager__c = :CaseManagerId
  AND RecordType.DeveloperName = 'Practitioner_Practice_Location'
  AND PRM_HealthcarePractitionerFacility__c != null

Output fields (via relationship traversal):
  CMA.Id                                                           --> CMAId
  CMA.PRM_HealthcarePractitionerFacility__c                       --> HCPFId
  HCPF.HealthcareFacilityId                                       --> HealthcareFacilityId
  HCPF.AccountId                                                  --> AccountId
  HCPF.PractitionerId                                             --> PractitionerId
  HCPF.IsActive                                                   --> HCPFIsActive
  HCPF.PRM_Pending__c                                             --> HCPFPending
  HCPF.RecordType.DeveloperName                                   --> HCPFRecordType
  HCPF.HealthcareFacility.Name                                    --> FacilityName
  HCPF.HealthcareFacility.PRM_Active__c                           --> FacilityActive
  HCPF.HealthcareFacility.PRM_TerminationDate__c                  --> FacilityTerminationDate
  HCPF.HealthcareFacility.BillingStreet                           --> FacilityStreet
  HCPF.HealthcareFacility.BillingCity                             --> FacilityCity
  HCPF.HealthcareFacility.BillingState                            --> FacilityState
  HCPF.HealthcareFacility.BillingPostalCode                       --> FacilityZip
  HCPF.Account.Name                                               --> GroupName

Formula output:
  HasTerminatedLocations = IF(COUNT(WHERE FacilityActive == false) > 0, true, false)
  TerminatedLocations = FILTER(results WHERE FacilityActive == false)
  ActiveLocations = FILTER(results WHERE FacilityActive == true)
  TotalLocationCount = COUNT(results)
  TerminatedLocationCount = COUNT(WHERE FacilityActive == false)

#### Affected Review Flow Components

Review Flow | Current DR (to be replaced / supplemented) | Change
App Review submit | PRMDREGetPLToPractitioner + PRMDREGetPracticeLocation | Replace CaseManager-based HCPF lookup with PRMDREGetPARCaseHCPFViaCMA. Pass HCPFId list to PRMDREGetPLToPractitioner for other operations.
PSV Review load | PRMDRGetPractionerPracticeLocation in PRM_FetchFormDetails_Procedure_28 | Add PRMDREGetPARCaseHCPFViaCMA as the first step; use its HCPFId output to drive the existing DR
QC Review load | PRMDRGetPractionerPracticeLocation (same shared IP) | Same as PSV
PDA Review load | PRMExtractPracticeLocationToPractitionerFacility in PRM_FetchFormPDAReview_Procedure_24 | Replace CaseManager filter with CMA-based lookup via PRMDREGetPARCaseHCPFViaCMA
Network Management QC | PRM_NetworkManagementQCUpdate (investigate first - US12) | TBD pending investigation

#### EligibleForUpdate COUNTQUERY Fix (PRMDREGetPracticeLocation)

The false-positive COUNTQUERY that triggers the Required Fields Missing error must also be fixed.
Use the CMA-derived HCPF Ids to guard the query:

Current COUNTQUERY:
  SELECT Count() FROM HealthcarePractitionerFacility
  WHERE HealthcareFacilityId = '{0}'
  AND PRM_Pending__c = true
  AND HealthcareFacility.PRM_Active__c = false

Updated COUNTQUERY:
  SELECT Count() FROM HealthcarePractitionerFacility
  WHERE HealthcareFacilityId = '{0}'
  AND PRM_Pending__c = true
  AND HealthcareFacility.PRM_Active__c = false
  AND Id NOT IN (
    SELECT PRM_HealthcarePractitionerFacility__c
    FROM PRM_CaseManagerAssociation__c
    WHERE PRM_CaseManager__c = '{1}'
    AND RecordType.DeveloperName = 'Practitioner_Practice_Location'
  )

Logic: Only flag a location as deleted-by-App-Review if the HCPF is NOT in the CMA
list for the current PAR case. If the HCPF IS in the PAR CMA list, it belongs to
this case and was terminated externally -- do NOT flag it as a user-deleted record.

Note: Verify DataRaptor COUNTQUERY supports subquery syntax. If not, the guard must be
implemented at the IP level as an If/Else Conditional Block before PRMDRPPractitionerDataUpdate
(the alternative approach documented in US4).

#### Integration Procedure Changes

IP | Change Required
PRM_FetchFormDetails_Procedure_28 (PSV, QC) | Add PRMDREGetPARCaseHCPFViaCMA call as first HCPF step; pass HCPFId list to existing HCPF DR. Gate on PRM_UseCaseManagerAssociation__c = true.
PRM_FetchFormPDAReview_Procedure_24 (PDA) | Same pattern.
PRM_ReviewPSVCaseRecordsUpdate v23 (App Review submit) | Pass current PAR IndividualApp Id to the updated EligibleForUpdate COUNTQUERY. Add If/Else guard before PRMDRPPractitionerDataUpdate using CMA membership check if COUNTQUERY subquery not supported.
App Review load IP (confirm name) | Add PRMDREGetPARCaseHCPFViaCMA as first step.

#### Acceptance Criteria

Scenario 1 -- PSV Review loads HCPF via CMA after PDM overwrote HCPF.PRM_CaseManager__c

Given HCPF.PRM_CaseManager__c was overwritten by PDM,
AND a CMA record exists with PRM_CaseManager__c = PAR case Id and PRM_HealthcarePractitionerFacility__c = HCPF.Id,
When PSV Review opens,
Then PRMDREGetPARCaseHCPFViaCMA returns the HCPF Id via the CMA record,
AND PSV Review displays all practice locations correctly.

---

Scenario 2 -- PDA Review loads HCPF via CMA (same conditions as Scenario 1)

Given same conditions,
When PDA Review opens,
Then PRMDREGetPARCaseHCPFViaCMA returns correct HCPF records for the case.

---

Scenario 3 -- App Review EligibleForUpdate does not false-positive on PAR-owned HCPF

Given HCPF is in the PAR case's CMA list,
AND HealthcareFacility.PRM_Active__c = false (terminated externally),
When App Review submit runs PRMDREGetPracticeLocation,
Then the updated COUNTQUERY (or IP-level guard) correctly excludes this HCPF,
AND EligibleForUpdate = false for this HCPF,
AND PRMDRPPractitionerDataUpdate does NOT fire,
AND App Review proceeds without Required Fields Missing error.

---

Scenario 4 -- Normal PAR case (no PDM interference) loads correctly (regression)

Given a PAR case where HCPF.PRM_CaseManager__c has NOT been overwritten,
AND CMA records exist (from US6),
When any review flow opens,
Then PRMDREGetPARCaseHCPFViaCMA returns the correct HCPF records via CMA,
AND all review steps function normally (no regression).

---

Scenario 5 -- Gate condition: flow gracefully handles PAR case with no CMA records (pre-migration)

Given a PAR IndividualApplication where PRM_UseCaseManagerAssociation__c = false
(CMA records not yet created - existing case before migration),
When any review flow opens,
Then the flow falls back to the existing HCPF direct query (PRM_CaseManager__c filter),
AND a warning or log entry is generated to flag this case for the migration batch,
AND no runtime error occurs.

#### Estimated Effort

Component | Effort | Notes
New DR PRMDREGetPARCaseHCPFViaCMA | M | New extract with CMA query + relationship traversal + formula outputs
Update PRMDREGetPracticeLocation COUNTQUERY (or IP guard) | S | Add CMA membership check; verify subquery syntax in DataRaptor
Update PRM_FetchFormDetails_Procedure_28 | S | Add CMA DR as first step; wire HCPFId list output
Update PRM_FetchFormPDAReview_Procedure_24 | S | Same pattern
Update PRM_ReviewPSVCaseRecordsUpdate v23 | S | Add PAR case Id input; add IP-level guard
Update App Review load IP | S | Add CMA DR as first step
Regression testing (all review flows) | L | Normal + PDM-overwritten + terminated + no-CMA-fallback
TOTAL | L |

---

### USER STORY 8 (Revised): App Review -- Show Terminated Location Warning on Step 1 Using CMA

Story Number: US8
Priority: P0 -- Direct business requirement, production blocker
Persona: Credentialing Specialist
OmniScript: PRM_InitialCredentialAppReview_English v28
Integration Procedure: App Review load IP
DataRaptor: PRMDREGetPARCaseHCPFViaCMA (from US7 - reused, no new DR needed)
Epic: PAR Case Manager Association via CMA Object
Depends On: US6 (CMA records exist), US7 (CMA-based HCPF lookup)

#### Story

As a Credentialing Specialist opening an App Review for a practitioner participation request,
I want the App Review to check -- on the VERY FIRST step -- whether any of the practice
locations linked to this PAR case (via CMA) have since been terminated,
And display a clear non-dismissable warning identifying the terminated location(s) with
two action options: "Update Locations" and "Close Case",
So that the specialist can make an informed decision at the start of the review rather
than hitting a Required Fields Missing error at the submit step.

#### How the Detection Works (Using CMA + US7 DR)

PRMDREGetPARCaseHCPFViaCMA already returns:
  HasTerminatedLocations (boolean)
  TerminatedLocations[] (array of terminated location objects with name, address, termination date)
  TerminatedLocationCount (integer)

The App Review load IP already calls this DR (added in US7).
US8 only needs to:
1. Read HasTerminatedLocations from the US7 DR output
2. If true: set response flag and pass TerminatedLocations list to OmniScript
3. OmniScript Step 1: show warning block when HasTerminatedLocations == true

No new DR is needed - the detection is built into PRMDREGetPARCaseHCPFViaCMA from US7.

#### Business-Approved Warning Message

"One or more practice locations selected on the original application for this practitioner
have been terminated. Please review the list below and either update the application to
select an active location, or close this case."

Terminated Location Display Table:
  Column 1: Practice Location Name
  Column 2: Address (Street, City, State, Zip)
  Column 3: Termination Date

#### Scope of Changes

Component | Type | Change
App Review load IP (confirm name) | IP - update | After calling PRMDREGetPARCaseHCPFViaCMA (US7), check HasTerminatedLocations output. If true: set response HasTerminatedLocations = true and TerminatedLocations list. This is a new If/Else branch after the existing CMA DR call.
PRM_InitialCredentialAppReview_English v28 | OmniScript - new Step 1 block | Add conditional display block at Step 1: Show when HasTerminatedLocations == true. Content: warning message + terminated location table (from TerminatedLocations[] array) + two action buttons.
"Update Locations" button | OmniScript action | Routes to location selection/edit experience (destination TBD per Question A1)
"Close Case" button | OmniScript action | Triggers App Review close IP with reason "Practice Location Terminated". Closes IndividualApplication. Updates HCPF records: IsActive=false, PRM_Pending__c=false. Optionally deletes or retains CMA records (per Question B1).

#### Acceptance Criteria

Scenario 1 -- Happy path: no terminated locations, App Review proceeds normally

Given all CMA-linked HCPF records for the PAR case have HealthcareFacility.PRM_Active__c = true,
When the Credentialing Specialist opens App Review,
Then PRMDREGetPARCaseHCPFViaCMA returns HasTerminatedLocations = false,
AND no warning is displayed,
AND App Review loads normally (no regression).

---

Scenario 2 -- Terminated location detected: warning on Step 1 (hard block)

Given at least one CMA-linked HCPF has HealthcareFacility.PRM_Active__c = false,
When the specialist opens App Review Step 1,
Then the warning message is shown with terminated location name, address, and termination date,
AND "Update Locations" and "Close Case" buttons are displayed,
AND the specialist CANNOT proceed to App Review content until they choose an action.

---

Scenario 3 -- User selects "Close Case": graceful closure

Given Scenario 2 (terminated location warning shown),
When the specialist clicks "Close Case",
Then a confirmation dialog appears:
  "Are you sure you want to close this case?
  Reason: Practice Location Terminated.",
AND upon confirmation: IndividualApplication.Status = Closed,
  HCPF records: IsActive=false, PRM_Pending__c=false,
AND success message: "Case IA-XXXXXXXXX closed. Reason: Practice Location Terminated."

---

Scenario 4 -- User selects "Update Locations": routed to edit experience

Given Scenario 2 (terminated location warning shown),
When the specialist clicks "Update Locations",
Then specialist is routed to the location selection/edit experience (TBD per Question A1),
AND upon saving updated locations, App Review can be re-opened and passes Step 1 check.

---

Scenario 5 -- Multiple terminated locations: all shown

Given a PAR case with 3 locations, 2 terminated,
When the specialist opens App Review,
Then both terminated locations appear in the warning table,
AND the 1 active location is NOT in the terminated table,
AND warning count reads: "2 practice locations have been terminated."

---

Scenario 6 -- Regression: production bug IA-0000096229 is resolved

Given IA-0000096229 has CMA records created by the migration batch (US6 Scenario 5),
AND the CMA links to HCPF for Regional Women's Health Group LLC
  (HealthcareFacility.PRM_Active__c = false),
When the specialist opens App Review,
Then the terminated location is caught at Step 1 (not at submit),
AND no Required Fields Missing error occurs,
AND the specialist sees the warning with Update Locations and Close Case options.

#### Estimated Effort

Component | Effort | Notes
App Review load IP - add terminated location detection branch | S | Read HasTerminatedLocations from US7 DR output; set response flags
PRM_InitialCredentialAppReview_English v28 - Step 1 warning UI | M | Warning block + table + two buttons + conditional display
Close Case IP integration | M | Wire to existing denial/close IP; add reason field
Update Locations routing | M-L | Depends on destination per Question A1
Regression testing (6 AC scenarios) | L | Full matrix
TOTAL | L-XL |

---

### USER STORY 9 (Revised): PSV Review -- Show Terminated Location Warning on Step 1

Story Number: US9
Priority: P0
Persona: PSV Reviewer
OmniScript: PRM_PrimarySourceVerificationReview_English v47
Integration Procedure: PSV load IP + PRM_ReviewPSVCaseRecordsUpdate v23
DataRaptor: PRMDREGetPARCaseHCPFViaCMA (from US7 - reused, no new DR)
Epic: PAR Case Manager Association via CMA Object
Depends On: US6, US7, US8

#### Story

As a PSV Reviewer opening a Primary Source Verification,
I want PSV Review to check on Step 1 whether any CMA-linked practice locations
have been terminated,
And display the same terminated-location warning with Update Locations and Close Case options,
So that PSV review is not blocked by downstream errors.

#### Scope of Changes

Component | Type | Change
PRMDREGetPARCaseHCPFViaCMA | DataRaptor Extract | NO CHANGE - reuse from US7
PSV Review load IP (confirm name) | IP - update | After calling PRMDREGetPARCaseHCPFViaCMA (added in US7), add same terminated location detection branch as US8
PRM_PrimarySourceVerificationReview_English v47 | OmniScript - new Step 1 block | Add same warning block as US8. Same two action buttons: Update Locations and Close Case.
Close Case button | Reuse close IP | Same as US8 - close with reason "Practice Location Terminated"
Update Locations button | Same routing as US8 | Same destination

#### Acceptance Criteria

All 6 scenarios from US8 apply with PSV Review as the context.

PSV-Specific Additional Scenario:

Scenario 7 -- PSV can still verify non-terminated locations when soft-block applies (per Question A3)

Given PSV Review loads with terminated location warning AND specialist chose to proceed,
When the PSV reviewer reviews data,
Then terminated location verification fields are marked "Location Terminated - Verification Not Required",
AND all other fields for active locations are reviewable.

#### Estimated Effort

Component | Effort | Notes
PSV load IP - terminated location detection branch | XS | Same pattern as US8; reuse US7 DR output
PSV OmniScript - Step 1 warning UI | S | Reuse warning component from US8
Regression testing | M | PSV-specific scenarios + shared regression
TOTAL | S |

---

### USER STORY 10 (Revised): QC Review -- Show Terminated Location Warning on Step 1

Story Number: US10
Priority: P0
Persona: QC Reviewer
OmniScript: PRM_PrimarySourceVerificationReview_English (CaseType = QC Review)
Integration Procedure: PRM_ReviewPSVCaseRecordsUpdate v23 (shared with PSV)
DataRaptor: PRMDREGetPARCaseHCPFViaCMA (from US7 - reused)
Epic: PAR Case Manager Association via CMA Object
Depends On: US6, US7, US8

#### Story

As a QC Reviewer opening a Quality Control review,
I want QC Review to show the terminated location warning on Step 1 (same pattern as App Review and PSV),
So that QC is not blocked and the reviewer can close or update the case before proceeding.

#### Scope of Changes

Component | Type | Change
PRMDREGetPARCaseHCPFViaCMA | DataRaptor Extract | NO CHANGE - reuse from US7
QC load IP / PRM_ReviewPSVCaseRecordsUpdate v23 | IP - confirm | If PSV detection branch (US9) is in the shared IP and fires for CaseType = QC Review too, no additional change. If QC has a separate load IP, add the same branch.
OmniScript QC path | OmniScript | Add same warning block + buttons if QC uses a separate step set from PSV.

#### Acceptance Criteria

All 6 scenarios from US8 apply with QC Review as context.

QC-Specific Additional Scenario:

Scenario 7 -- QC can still review non-terminated locations

Given QC case with 1 terminated + 1 active location, reviewer chose to proceed,
When QC reviewer accesses review fields,
Then terminated location shown read-only with badge "Terminated",
AND active location fields are fully editable and reviewable.

#### Estimated Effort

Component | Effort | Notes
QC load IP detection branch | XS | Confirm/reuse from US9 shared IP
QC OmniScript warning block | S | Reuse from US8/US9 if separate OmniScript
Regression testing | M | QC matrix + shared regression
TOTAL | XS-S |

---

### USER STORY 11 (Revised): PDA Review and Update -- Stable HCPF Fetch via CMA and Informational Terminated Location Warning

Story Number: US11
Priority: P1
Persona: PDA Reviewer (Provider Data Analyst)
OmniScript: PRM_InitialCredPDAQC_English v15 (FlowType = "PDA Review and Update")
Integration Procedure: PRM_FetchFormPDAReview_Procedure_24 (fetch) + PRM_InitialCredPDAReviewUpdate_Procedure_23 (submit)
DataRaptor to change: PRMExtractPracticeLocationToPractitionerFacility (step 5 of fetch IP)
DataRaptor reused: PRMDREGetPARCaseHCPFViaCMA (from US7)
Epic: PAR Case Manager Association via CMA Object
Depends On: US6 (CMA records exist for PAR cases), US7 (CMA-based DR built)

#### What PDA Review Does (Context)

PDA Review and Update is the data accuracy review step before Network Management QC.
The PDA (Provider Data Analyst):
  1. Reviews all HCPF records, networks, PPLTN records, directory indicators, taxonomy-network linkages
  2. Confirms or updates the values (Show In Directory, networks, info codes, role, taxonomy)
  3. On submit:
     - Closes the current PDA Review Case (Status = Closed)
     - Updates the IndividualApplication: PRM_Stage__c = "Network Management QC"
     - Auto-creates a new Case of Type = "Network Management QC"
     - Updates HCPF and PPLTN records via PRM_InitialCredPDAReviewUpdateSubIPInsert + SubIPUpdate

PDA is the LAST review step before activation. A terminated location at this stage means
the committee already approved the location but it got terminated via a Provider Change
AFTER committee approval. PDA needs to see this information to make an informed decision --
but it is NOT a hard block. PDA can still complete the review and advance to Network Management QC.
The terminated location is flagged informally and handled at the PDA-to-QC handoff.

#### Story

As a PDA Reviewer opening a PDA Review and Update case,
I want the PDA Review to load all HCPF records via the stable CMA link
(PRM_CaseManagerAssociation__c.PRM_HealthcarePractitionerFacility__c) rather than
the HCPF.PRM_CaseManager__c field directly (which may have been overwritten by PDM),
AND to display an informational notice -- not a hard block -- when any of those locations
have been terminated since the PAR was submitted,
So that the PDA Reviewer sees the complete and correct set of practice locations for the case,
is aware of any terminated locations before confirming data, and can still complete
the PDA Review without being blocked.

#### Why CMA Is the Primary Goal Here

The current HCPF-loading DR for PDA (PRMExtractPracticeLocationToPractitionerFacility, step 5
of PRM_FetchFormPDAReview_Procedure_24) filters:

  HealthcarePractitionerFacility WHERE PRM_CaseManager__c = CaseManagerId
  AND PractitionerId = PractitionerId
  AND IsActive = true
  AND RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'

After PDM overwrites HCPF.PRM_CaseManager__c, this query returns ZERO ROWS.
The PDA reviewer sees an empty practice location section and cannot confirm or activate records.

The CMA-based approach resolves HCPF Ids from the immutable CMA junction:
  PRM_CaseManagerAssociation__c WHERE PRM_CaseManager__c = CaseManagerId
  AND RecordType.DeveloperName = 'Practitioner_Practice_Location'
  → yields HCPF Ids regardless of what PDM did to HCPF.PRM_CaseManager__c

The PRMDREGetPARCaseHCPFViaCMA DR (built in US7) provides these Ids AND flags
which locations have HealthcareFacility.PRM_Active__c = false (terminated).

#### Terminated Location: Informational Warning (Not Hard Block)

Business direction: PDA can show the locations are terminated but the reviewer should
still be able to proceed and complete the PDA Review.

The terminated location notice appears ON THE PDA REVIEW SCREEN (not as a Step 1 hard block):
  - Above the Practice Location table, show an amber/warning banner:
    "Notice: The following practice locations associated with this application have been
    terminated via a Provider Change Request. Please review and confirm the data below."
  - The terminated location rows in the practice location table are displayed with a
    visual indicator (e.g., "Terminated" badge, greyed-out row, or amber highlight)
  - The terminated location rows are READ-ONLY in the table (cannot be edited by PDA)
  - Active locations remain fully editable (network, directory, taxonomy fields)
  - The PDA reviewer can still click Submit to complete the review and advance to
    Network Management QC -- there is NO block on submission

The PDA reviewer's available actions:
  A. Note the terminated location, complete the review for active locations, submit to NMQC
  B. (If business decides to add this later) Flag the case for admin review before submitting

#### Scope of Changes

Component | Type | Change
PRMDREGetPARCaseHCPFViaCMA (US7 DR) | DataRaptor Extract | NO CHANGE to the DR itself -- already built in US7 with HasTerminatedLocations, TerminatedLocations[], ActiveLocations[], HCPFId list
PRM_FetchFormPDAReview_Procedure_24 (v24) | IP - add CMA step BEFORE step 5 | Add PRMDREGetPARCaseHCPFViaCMA as a new step (seq 4.5) with input CaseManagerId. Output: HCPFIdList (from CMA), HasTerminatedLocations, TerminatedLocations[]. Gate: only runs when PRM_UseCaseManagerAssociation__c = true AND RCDeveloperName = PRM_PractitionerParticipationRequest or PRM_PNC.
PRMExtractPracticeLocationToPractitionerFacility (step 5 of fetch IP) | DR - update input source | Change input for step 5 from CaseManagerId-based filter to HCPFId-list-based filter. Add new input: HCPFIdList from the CMA DR (step 4.5). Add new filter group: Id IN :HCPFIdList (in addition to or replacing the PRM_CaseManager__c = CaseManagerId filter).
PRM_FetchFormPDAReview_Procedure_24 (v24) | IP - add terminated location response flag | After step 4.5, if HasTerminatedLocations = true: set TerminatedLocations and HasTerminatedLocations in the Response output. These are passed to the OmniScript.
PRM_InitialCredPDAQC_English v15 | OmniScript - PDA path | Add an amber banner element on the PracticeLocation step (NOT on Step 1 as a hard block). Show when HasTerminatedLocations == true AND FlowType == "PDA Review and Update". Banner content: terminated location list with name + address + termination date. Practice location table rows where HealthcareFacility.PRM_Active__c = false rendered as read-only with "Terminated" badge.

#### Data Flow with CMA (Updated Step 5)

Before (broken when PDM overwrites PRM_CaseManager__c):
  Step 5 PRMExtractPracticeLocationToPractitionerFacility
    Input: CaseManagerId = DRExtractCaseDetails:CaseManagerId
    Filter: HCPF WHERE PRM_CaseManager__c = CaseManagerId AND IsActive = true
    Problem: returns ZERO ROWS after PDM overwrites HCPF.PRM_CaseManager__c

After (stable via CMA):
  NEW Step 4.5 PRMDREGetPARCaseHCPFViaCMA
    Input: CaseManagerId = DRExtractCaseDetails:CaseManagerId
    Query: CMA WHERE PRM_CaseManager__c = CaseManagerId
           AND RecordType = Practitioner_Practice_Location
    Output: HCPFIdList = [HCPF.Id, HCPF.Id, ...]
            HasTerminatedLocations = true/false
            TerminatedLocations[] = [{FacilityName, Address, TerminationDate}, ...]

  Updated Step 5 PRMExtractPracticeLocationToPractitionerFacility
    Input: HCPFIdList from step 4.5 (NEW input path)
    Filter: HCPF WHERE Id IN :HCPFIdList (replaces PRM_CaseManager__c filter)
    Returns: all HCPF records for this PAR case regardless of PRM_CaseManager__c state

The downstream steps 6-24 continue to work unchanged because they receive
the same HCPF/HCF list in the same output nodes as before -- the change is only
in HOW step 5 resolves the HCPF records.

#### Acceptance Criteria

Scenario 1 -- PDA Review loads HCPF correctly after PDM overwrote PRM_CaseManager__c

Given HCPF.PRM_CaseManager__c was overwritten by a PDM termination (to PDM IndividualApp Id),
AND CMA records exist for the PAR case (PRM_CaseManager__c = PAR IndividualApp Id,
    PRM_HealthcarePractitionerFacility__c = HCPF.Id),
When the PDA Reviewer opens the PDA Review case,
Then step 4.5 (PRMDREGetPARCaseHCPFViaCMA) resolves HCPFIdList from CMA,
AND step 5 (PRMExtractPracticeLocationToPractitionerFacility) queries by HCPFIdList
    and returns the correct HCPF records,
AND all practice locations for the PAR case are displayed in the PDA Review screen.

---

Scenario 2 -- PDA Review shows terminated location informational banner (not hard block)

Given at least one CMA-linked HCPF has HealthcareFacility.PRM_Active__c = false,
When the PDA Reviewer opens the PDA Review,
Then an amber informational banner appears above the practice location table:
    "Notice: One or more practice locations associated with this application have been
    terminated via a Provider Change Request. Please review the data below.",
AND the terminated location rows in the practice location table are visible
    with a "Terminated" badge and are rendered read-only (cannot be edited),
AND active locations remain fully editable (networks, directory, taxonomy fields),
AND the PDA Reviewer CAN click Submit without any block -- the terminated location
    warning is informational only.

---

Scenario 3 -- PDA Review submits normally and creates Network Management QC case

Given the PDA Review contains a terminated location (informational warning shown),
When the PDA Reviewer completes the review and clicks Submit,
Then PRM_InitialCredPDAReviewUpdate_Procedure_23 runs normally:
    - Current PDA Case closed (Status = Closed),
    - IndividualApplication.PRM_Stage__c = "Network Management QC",
    - New Case of Type = "Network Management QC" created,
    - HCPF and PPLTN records updated with confirmed network/directory/taxonomy values,
AND the terminated location's HCPF record is NOT activated (IsActive remains false),
AND the active location HCPF records ARE processed and updated normally.

---

Scenario 4 -- PDA Review with no terminated locations (regression - normal path)

Given all CMA-linked HCPF records have HealthcareFacility.PRM_Active__c = true,
When the PDA Reviewer opens the PDA Review,
Then no terminated location banner is shown,
AND all practice locations are editable,
AND the PDA Review behaves exactly as before (no regression).

---

Scenario 5 -- Multiple practice locations, only some terminated

Given a PAR case with 3 practice locations: 2 active, 1 terminated,
When the PDA Reviewer opens the PDA Review,
Then the informational banner lists only the 1 terminated location,
AND the 2 active locations are displayed normally and fully editable,
AND the 1 terminated location row is read-only with "Terminated" badge,
AND PDA can edit and confirm the 2 active locations without restriction,
AND PDA can submit the review based on the 2 active locations.

#### Estimated Effort

Component | Effort | Notes
PRM_FetchFormPDAReview_Procedure_24 - add step 4.5 (CMA call) | S | Add PRMDREGetPARCaseHCPFViaCMA step before step 5; wire CaseManagerId input
PRMExtractPracticeLocationToPractitionerFacility - update filter to HCPFIdList | S | Change filter input from CaseManagerId to HCPFIdList; verify downstream step compatibility
PRM_FetchFormPDAReview_Procedure_24 - add terminated location detection branch | S | If HasTerminatedLocations = true, add TerminatedLocations to response; same pattern as US8
PRM_InitialCredPDAQC_English v15 - amber banner on PracticeLocation step | M | Conditional banner element (not Step 1 hard block); terminated rows in table as read-only with badge; FlowType-gated to PDA path
Verify downstream steps 6-24 receive same output structure | S | Confirm step 6 (DRExtractFacility) still gets FacilityIdList from step 5 correctly
Regression testing (5 AC scenarios) | L | Normal + PDM-overwritten + terminated + multi-location + submit path
TOTAL | M-L |

---

### USER STORY 12 (Revised): Network Management QC -- CMA-Based Fetch and Informational Terminated Location Notice

Story Number: US12
Priority: P1 (elevated from P2 - investigation is COMPLETE, this is largely covered by US11)
Persona: Network Management QC Reviewer
OmniScript: PRM_InitialCredPDAQC_English v15 (FlowType = "Network Management QC")
Integration Procedure: PRM_FetchFormPDAReview_Procedure_24 (fetch - SHARED WITH PDA)
                       PRM_InitialCredPDAReviewUpdate_Procedure_23 (submit - SHARED WITH PDA)
Epic: PAR Case Manager Association via CMA Object
Depends On: US6, US7, US11

#### Key Investigation Findings (No Longer "Investigation-First")

The investigation is COMPLETE. Here is what was confirmed:

1. There is NO separate "PRM_NetworkManagementQCUpdate" IP.
   Network Management QC uses the SAME Integration Procedures as PDA Review:
   - Fetch: PRM_FetchFormPDAReviewParent -> PRM_FetchFormPDAReview_Procedure_24 (SAME)
   - Submit: PRM_InitialCredPDAReviewUpdateParent -> PRM_InitialCredPDAReviewUpdate_Procedure_23 (SAME)

2. Network Management QC uses the SAME OmniScript as PDA Review:
   PRM_InitialCredPDAQC_English v15. The OmniScript branches on FlowType:
   - FlowType = "PDA Review and Update" --> PDA Review path
   - FlowType = "Network Management QC" --> NMQC path (different steps shown, same data load)
   The "SetFlowValue" element hard-codes FlowType = "Network Management QC" for NMQC.

3. Network Management QC loads PAR-originated HCPF records:
   Step 5 of PRM_FetchFormPDAReview fires when:
     RCDeveloperName == 'PRM_PractitionerParticipationRequest' (PAR)
     OR RCDeveloperName == 'PRM_PNC'
   The same CaseManagerId chain is used. NMQC reviewers see the SAME HCPF/PPLTN/HCF
   data set that the PDA just confirmed.

4. NMQC is a REVIEW-ONLY outcome step:
   - QC Completed: closes case, IndividualApplication.Status = Approved, Stage = Complete
   - Errors Found: sends back to PDA (creates new PDA Review and Update Case)
   - Rebuttal: places Case in Pended-Rebuttal status

5. CONSEQUENCE: Because NMQC and PDA share the same fetch IP,
   the CMA-based HCPF resolution added in US11 (step 4.5 in PRM_FetchFormPDAReview)
   AUTOMATICALLY applies to NMQC as well. US12 is mostly about:
   - Verifying the warning banner is correctly displayed for the NMQC FlowType
   - Confirming the NMQC outcome paths work correctly when terminated locations are present
   - Ensuring the NMQC outcome logic (QC Completed / Errors Found / Rebuttal) is not
     affected by the presence of terminated location data in the response payload

#### Story

As a Network Management QC Reviewer reviewing a practitioner participation case,
I want the Network Management QC screen to load all HCPF records via the stable
CMA-based fetch (automatically inherited from US11's PDA Review fix),
AND to display an informational notice -- not a block -- when any of the practice
locations have been terminated since the PAR was submitted,
So that I have full visibility into the practice location status when making my QC
outcome decision (QC Completed / Errors Found), without being prevented from
completing the review.

#### Why NMQC Is a Show-Message, No-Block Scenario

Business direction: "they are just reviewing the data, so we can show the message"

NMQC is a quality control review: the reviewer checks that the networks, directory
indicators, and taxonomy data were correctly configured by the PDA. Their output is
a binary decision (QC Completed or Errors Found). A terminated location is factual
data they need to be aware of when making that decision -- but it does not block
either outcome path. If the QC reviewer believes the terminated location is a
material issue, they can choose "Errors Found" and send it back to PDA with a
note. That business decision belongs to the reviewer, not the system.

#### Scope of Changes (What US11 Provides Automatically vs. What US12 Adds)

Component | Provided by | Change
CMA-based HCPF fetch (step 4.5 in PRM_FetchFormPDAReview) | US11 | Already in place - NMQC uses same fetch IP
HasTerminatedLocations + TerminatedLocations[] in IP response | US11 | Already in place - same response from same IP
PRM_InitialCredPDAQC_English v15 - FlowType-gated warning banner | US12 | The US11 amber banner is gated FlowType == "PDA Review and Update". US12 adds the SAME banner for FlowType == "Network Management QC" -- OR -- the banner element is updated to show for BOTH FlowType values (PDA Review and Update OR Network Management QC)
NMQC outcome paths: verify QC Completed / Errors Found / Rebuttal paths unaffected | US12 | Regression verification that the terminated location data in the response payload does not break the SetRecordsQCCompleted or SetRecordsNtwlMgntQC Set Values steps or the IPPNCRecordsUpdate submit call
NMQC review screen terminated rows | US12 | Confirm terminated location rows display with "Terminated" badge and are read-only in the NMQC-specific practice location table elements (PracticeLocDirTable, PracticeLocNtwkDirTable, PPLStep PPLTN table)

#### OmniScript Warning Banner: Single Element Covering Both Flows

Rather than two separate banner elements (one for PDA, one for NMQC), the implementation
should use a single reusable element with show condition:

  Show when: HasTerminatedLocations == true
             AND (FlowType == "PDA Review and Update" OR FlowType == "Network Management QC")

Banner text (same for both flows):
  "Notice: One or more practice locations associated with this application have been
  terminated via a Provider Change Request. The terminated location(s) are shown below
  for reference and cannot be edited."

This is simpler to maintain and guarantees consistent behavior across both flows.

#### Scope of Changes (US12 Only -- US11 changes already in place)

Component | Type | Change
PRM_InitialCredPDAQC_English v15 | OmniScript - update banner show condition | Change existing US11 banner show condition from FlowType == "PDA Review and Update" to (FlowType == "PDA Review and Update" OR FlowType == "Network Management QC"). OR: build the element once with both FlowType values in its condition.
PRM_InitialCredPDAQC_English v15 - NMQC practice location table steps | OmniScript - verify | Confirm that PracticeLocDirTable, PracticeLocNtwkDirTable, and PPLStep table elements in the NMQC path correctly render terminated rows as read-only with "Terminated" badge (should inherit from the same element bindings used in PDA path).
NMQC outcome regression: SetRecordsQCCompleted | OmniScript Set Values - verify | Confirm this step (which writes Case Status=Closed, IndividualApplication PRM_Stage__c=Complete, Status=Approved) is unaffected by HasTerminatedLocations being true. No change expected.
NMQC outcome regression: SetRecordsNtwlMgntQC (Errors Found) | OmniScript Set Values - verify | Confirm this step (which writes PRM_Stage__c=PDA Review and Update, creates new PDA Case) is unaffected. QC reviewer can choose Errors Found and note the terminated location in the QC notes.
NMQC outcome regression: Rebuttal path | OmniScript Set Values - verify | Confirm unaffected.
IPPNCRecordsUpdate submit | IP Action - verify | Confirm PRM_InitialCredPDAReviewUpdate_Procedure_23 accepts the response payload with terminated location data present (extra fields in payload should be ignored).

#### NMQC Outcome Behaviors with Terminated Locations

Outcome | Expected Behavior
QC Completed | NMQC reviewer approves the case. IndividualApplication Status=Approved, Stage=Complete. The terminated location HCPF record was already read-only and excluded from activation. The active HCPF records are finalized. No block.
Errors Found | NMQC reviewer can note in QC notes that a terminated location is an issue and send back to PDA. PDA receives a new Returned Case. The terminated location continues to be shown informally. No automated behavior change for terminated locations.
Rebuttal | Case pended. No change to HCPF records. Terminated location remains flagged informally.

#### Acceptance Criteria

Scenario 1 -- NMQC loads HCPF via CMA (inherited from US11, regression verification)

Given HCPF.PRM_CaseManager__c was overwritten by PDM,
AND CMA records exist for the PAR case,
When the NMQC Reviewer opens the Network Management QC case
    (PRM_InitialCredPDAQC_English, FlowType = "Network Management QC"),
Then PRM_FetchFormPDAReview step 4.5 resolves HCPF Ids via CMA,
AND step 5 queries by HCPFIdList,
AND the practice locations are displayed correctly in the NMQC screen.

---

Scenario 2 -- Terminated location informational banner shown in NMQC

Given at least one CMA-linked HCPF has HealthcareFacility.PRM_Active__c = false,
When the NMQC Reviewer opens the NMQC case,
Then the amber informational banner appears:
    "Notice: One or more practice locations associated with this application have been
    terminated via a Provider Change Request. The terminated location(s) are shown below
    for reference and cannot be edited.",
AND the terminated location rows in the NMQC practice location table display
    with a "Terminated" badge and are read-only,
AND the NMQC Reviewer CAN still choose "QC Completed" or "Errors Found" without any block.

---

Scenario 3 -- QC Completed outcome unaffected by terminated location

Given terminated location banner is shown in NMQC,
When the NMQC Reviewer selects "QC Completed" and submits,
Then SetRecordsQCCompleted runs: Case Status=Closed, IndividualApplication Status=Approved,
    PRM_Stage__c=Complete,
AND IPPNCRecordsUpdate runs PRM_InitialCredPDAReviewUpdate_Procedure_23 successfully,
AND no error is thrown due to terminated location data in the payload,
AND the case is successfully completed and the practitioner record is finalized.

---

Scenario 4 -- Errors Found outcome: NMQC reviewer can note terminated location

Given terminated location banner is shown in NMQC,
When the NMQC Reviewer selects "Errors Found", enters QC notes
    (e.g. "Practice location terminated -- PDA to review"), and submits,
Then SetRecordsNtwlMgntQC runs: Case Status=Closed,
    IndividualApplication PRM_Stage__c="PDA Review and Update",
    new PDA Review and Update Case created (Returned status),
AND IPPNCRecordsUpdate runs successfully,
AND the case returns to PDA with the QC notes visible.

---

Scenario 5 -- No terminated locations: NMQC loads and submits normally (regression)

Given all CMA-linked HCPF records have HealthcareFacility.PRM_Active__c = true,
When the NMQC Reviewer opens the NMQC case,
Then no terminated location banner is shown,
AND all NMQC outcome paths (QC Completed / Errors Found / Rebuttal) work exactly
    as before (no regression).

#### Estimated Effort

Component | Effort | Notes
Update banner show condition in PRM_InitialCredPDAQC_English v15 | XS | Add FlowType == Network Management QC to existing US11 banner condition
Verify NMQC table elements render terminated rows correctly | XS | Read OmniScript element bindings -- likely already correct as same data shape
Regression verify SetRecordsQCCompleted | XS | Read Set Values step -- no change expected
Regression verify SetRecordsNtwlMgntQC (Errors Found) | XS | Read Set Values step -- no change expected
Regression verify IPPNCRecordsUpdate with terminated location payload | S | Run end-to-end test in sandbox
Regression testing (5 AC scenarios) | M | NMQC-specific scenarios + full outcome matrix
TOTAL | S-M | Bulk of work is US11; US12 is primarily verification + one condition update

---

## 6. Story Dependencies and Sprint Order

Dependency Tree:

  US6 (PAR form creates CMA records + data migration batch)
  US7 (PRMDREGetPARCaseHCPFViaCMA + review flow DR/IP updates)   DEPLOY US6 + US7 TOGETHER
       |
       +-- US8 (App Review Step 1 warning)     P0 - production blocker
       |     |
       |     +-- US9  (PSV Review Step 1 warning)  reuses US7 DR + US8 warning component
       |     +-- US10 (QC Review Step 1 warning)   reuses US7 DR + US8 warning component
       |
       +-- US11 (PDA Review - CMA load + Step 1 warning)

  US12 (Network Management QC - inherits CMA fetch from US11; banner condition update + regression verification)

Recommended Sprint Order:

Sprint | Stories | Rationale
Sprint 1 | US6 + US7 | Foundation: CMA creation in PAR form + CMA-based DR for all reviews. Deploy together.
Sprint 2 | US8 | App Review Step 1 warning - unblocks production bug immediately
Sprint 2 | US9 + US10 | PSV and QC warnings - same component/pattern; same sprint as US8
Sprint 3 | US11 | PDA - depends on US6/US7 confirmed in production
Sprint 3 | US12 | Network Management QC - investigation + conditional change

---

## 7. What Changes vs. What Stays the Same

### Changes

Component | Change
PRM_CaseManagerAssociationService.cls | New method createCMAsForPARHCPF() for PAR form CMA creation
PRM_CreatePractitionerAddressRecords v41 | Add Remote Action step to create CMA after HCPF creation
PRM_PractitionerAddressCreation v3 | Same
New Batch: PRM_PARCMABackfillBatch.cls | One-time migration to create CMA for existing in-flight PAR cases
New DR: PRMDREGetPARCaseHCPFViaCMA | New CMA-based HCPF resolver with terminated location detection built in
PRMDREGetPracticeLocation COUNTQUERY | Add CMA membership guard to prevent false-positive EligibleForUpdate
PRM_FetchFormDetails_Procedure_28 (PSV, QC) | Add PRMDREGetPARCaseHCPFViaCMA as first step; add detection branch
PRM_FetchFormPDAReview_Procedure_24 (PDA) | Same
App Review load IP | Add PRMDREGetPARCaseHCPFViaCMA as first step; add detection branch
PRM_ReviewPSVCaseRecordsUpdate v23 | Add PAR CMA guard for EligibleForUpdate false-positive
App Review / PSV / QC / PDA OmniScripts | New Step 1 terminated location warning block (reused component)

### Does NOT Change

Component | Why Not Changed
HCPF.PRM_CaseManager__c field on HealthcarePractitionerFacility | PDM and PCR flows continue writing to it - operational behavior unchanged and unaffected
PRMDRLoadUpdateHCPF | Continues writing PDM CaseManager to HCPF.PRM_CaseManager__c - no change needed
PRM_PracLocTermHelper.cls (Provider Change batch, lines 264-299) | Operational termination logic unchanged
Existing PDM CMA creation flows | PDM already creates CMA records - those paths untouched
PRMDRCreateHealthcarePractitionerFacility | HCPF creation unchanged - CMA creation is a NEW parallel step in the calling IP
PRMExtractCaseDetails | Continues reading Case.PRM_CaseManager__c and passing as CaseManagerId to IPs
PRM_CaseManagerRelatedListController.cls | UI display of CMA records unchanged
prmCaseManagerRelatedList LWC | UI component unchanged
PRM_NetworkManagementQCUpdate | Does NOT exist as a separate IP (confirmed by investigation). NMQC shares PRM_FetchFormPDAReview_Procedure_24 and PRM_InitialCredPDAReviewUpdate_Procedure_23 with PDA Review. No separate IP change needed.
Daily script (bug 1331370) | Separate fix covered in US5 (active location guard before stamping)

---

## 8. Key Design Decisions Summary

Decision | Choice | Rationale
New field vs. existing object | Reuse PRM_CaseManagerAssociation__c | No new field needed; existing object already has PRM_HealthcarePractitionerFacility__c lookup; existing Apex builder (PRM_CaseManagerAssociationDirectBuilder.createCMAForPractitionerPracticeLocation()) already does the right thing; aligns with how PDM tracks its records
CMA creation method | Extend PRM_CaseManagerAssociationService | Reuse tested, production-proven code path; same deduplication pattern; same flag-setting logic
HCPF resolution in review flows | New DR PRMDREGetPARCaseHCPFViaCMA querying CMA | Single DR for all review flows; relationship traversal in one query; terminated location detection built in as formula output; no need for separate terminated location DR
EligibleForUpdate guard | Add CMA membership check to COUNTQUERY (or IP guard) | Prevents false-positive Required Fields Missing error; CMA membership is more precise than PRM_CaseManager__c equality check since CMA is immutable to PDM changes
PDM CMA creation | No change | PDM already creates CMA correctly; no risk of cross-contamination

---

End of Document
Document created: April 29, 2026
Architecture Decision: Reuse PRM_CaseManagerAssociation__c (PRM_HealthcarePractitionerFacility__c lookup) instead of new field
