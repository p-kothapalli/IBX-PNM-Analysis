# PNM Off Cycle PDA Review & Update — Apex Service Architecture

## IP Audit, Reusability Matrix & New Service Blueprint (Post-Committee Review)

> **Companion docs**
> - `PNM_Apex_Service_Architecture.md` — generic SOA framework.
> - `PNM_ParForm_RecordCreation_Apex_Service_Architecture.md` — Practitioner Participation Form (the proven model).
> - `PNM_PDA_ReviewUpdate_Apex_Service_Architecture.md` — **Initial Cred** PDA Review/Update (the closest sibling — same pattern, different domain).
> - `PNM_OffCycle_Process_Apex_Service_Architecture.md` — Off Cycle **submit** flow (its services are heavily reused here).
>
> This document covers the **post-committee** path for an Off Cycle case: after the practitioner-update form has been submitted, the case flows through QM Review → PDA Outcome → optional Network QC Review. It is the mirror image of `PNM_PDA_ReviewUpdate_Apex_Service_Architecture.md` but for Off Cycle outcomes (which are richer — Network QC actually executes the bulk of the record changes here, not at submit time).

---

## 0. TL;DR

| | Initial Cred PDA Review | **Off Cycle PDA Review** |
|---|---|---|
| Entry OmniScript | `PRM_InitialCredPDA_English` | **`PRM_OffCyclePDAReview_English`** (active v16) + **`PRM_OffCycleQCReview_English`** (active v13) |
| Container IP | `PRM_InitialCredPDAReviewUpdateParent` | **`PRM_OffCycleRecordUpdatesPDAReviewParent`** (4 elt) <br> **`PRM_OffCycleRecordUpdatesQCReviewContainer`** (4 elt) <br> **`PRM_OffCycleCaseCaseMgrUpdatesSendToPDAParent`** (4 elt) |
| Orchestrator IPs | `PRM_InitialCredPDAReviewUpdate` (10) + `SubIPInsert` (28) + `SubIPUpdate` (21) + `HFN` (2) | **`PRM_OffCycleRecordUpdatesPDAReview`** (38 elt) <br> **`PRM_OffCycleRecordUpdatesQCReview`** (5 elt) <br> **`PRM_OffCycleCaseCaseMgrUpdatesSendToPDA`** (4 elt) |
| Variant axis | PDA Outcome (Approve / Reroute / NetworkQC) | **`PDAOutCome`** picklist (`Approve` / `RerouteToQM` / `NetworkQC`) **× `ChangeRequested`** (Role / Specialty / NewState / NewRegion / Name / Demographics / Reinstate / Term) |
| Heaviest single IP | SubIPInsert (28) | **`PRM_OffCycleRecordUpdatesPDAReview`** (38) — both branches in one IP |
| Record-creation responsibility | High (HCFN/HCF/PNC inserts here) | **Very high** — for `PDAOutCome=NetworkQC` the IP performs every State/Region facility/loc/address/group-HCPF insert + HCFN insert + taxonomy update + NPI history update + practitioner update |
| DML pattern | INSERT + UPDATE | INSERT (HCF/Loc/Addr/HCPF/HCFN/HCPNPI/HCPT) + UPDATE (~9 SObjects) |
| Reusable framework code | ~70% | **~80%** — both Par Form and Off Cycle Submit services are direct inputs |
| Net-new services needed | 6 PDA-specific | **~5 Off-Cycle-PDA-specific** services + 0 new selectors (all needed selectors already exist after Off Cycle Submit lands) |

---

## 1. Current State: Complete IP Chain Audit

### 1.1 The three-stage post-committee chain

The Off Cycle case touches **three** OmniScripts (and three IP container pairs) after the original submit:

```
   ┌────────────────────────────────────────────────────────────────────┐
   │  STAGE 1 — QM Review (Send to PDA)                                  │
   │                                                                     │
   │  OmniScript:  PRM_OffCycleQMReview_English / PRM_OffCycleQCReview   │
   │     │                                                                │
   │     │  user enters QM note + selects "Send to PDA"                  │
   │     ▼                                                                │
   │  IP: PRM_OffCycleCaseCaseMgrUpdatesSendToPDAParent  (Container)     │
   │  IP: PRM_OffCycleCaseCaseMgrUpdatesSendToPDA  (4 elements)          │
   │     ├─ DRCreateNewCaseRecord ─ DR Post: create the "PDA" case       │
   │     ├─ DRUpdateCaseCaseMgr ─── DR Post: update old case + case mgr  │
   │     ├─ RA_CreateNote ───────── Remote Action: PRM_OmniUtils.createNoteMulti
   │     └─ Response                                                     │
   └────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
   ┌────────────────────────────────────────────────────────────────────┐
   │  STAGE 2 — PDA Review (decide the outcome)                          │
   │                                                                     │
   │  OmniScript:  PRM_OffCyclePDAReview_English  (active v16)            │
   │     │                                                                │
   │     │  user picks PDAOutCome ∈ {Approve, RerouteToQM, NetworkQC}    │
   │     │  enters notes, optional file uploads, network/info-code edits  │
   │     ▼                                                                │
   │  IP: PRM_OffCycleRecordUpdatesPDAReviewParent  (Container)          │
   │  IP: PRM_OffCycleRecordUpdatesPDAReview  (**38 elements**)           │
   │     ├─ ConditionalBlockNetMgmntQC   (%PDAOutCome% == "NetworkQC")    │
   │     │     └─ 23 nested elements (the WHOLE record-update payload)   │
   │     ├─ ConditionalBlockReRouteToQM  (%PDAOutCome% == "RerouteToQM")  │
   │     │     └─ 4 nested elements (case creation + identifier + note)  │
   │     └─ (Approve outcome → just the Response — no record writes)      │
   └────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
   ┌────────────────────────────────────────────────────────────────────┐
   │  STAGE 3 — Network QC Review (only when PDA picked "NetworkQC")     │
   │                                                                     │
   │  OmniScript:  PRM_OffCycleQCReview_English  (active v13)             │
   │     │                                                                │
   │     │  Network QC reviewer reviews the changes PDA made              │
   │     │  and signs off (or sends back).                                │
   │     ▼                                                                │
   │  IP: PRM_OffCycleRecordUpdatesQCReviewContainer  (Container)         │
   │  IP: PRM_OffCycleRecordUpdatesQCReview  (5 elements)                 │
   │     ├─ CreateNewCaseQc ─────── DR Post: create the QC Review case   │
   │     ├─ UpdateCaseCaseMgr ───── DR Post: close prior case            │
   │     ├─ RA_CreateContentNote ── Remote Action: PRM_OmniUtils         │
   │     ├─ PRMDRCreateIdentiferAndDocument ─ DR Post: identifier+doc    │
   │     └─ ResponseQC                                                   │
   └────────────────────────────────────────────────────────────────────┘
```

### 1.2 STAGE 1 — `PRM_OffCycleCaseCaseMgrUpdatesSendToPDA` (4 elements)

| # | Element | Type | Bundle / RA | Purpose | Notes |
|---|---|---|---|---|---|
| 01 | `DRCreateNewCaseRecord` | DR Post | `PRMCreateNewCase` | Creates the "PDA" Case row (RecordType = PDA Review for Off Cycle) | always |
| 02 | `DRUpdateCaseCaseMgr` | DR Post | `PRMUpdateCaseCaseMgrOffCycleSendToPDA` | Updates the QM case's CaseManager + Status, links new case | always |
| 03 | `RA_CreateNote` | Remote Action | `PRM_OmniUtils.createNoteMulti` | Persists the QM note onto the new case | always |
| 04 | `Response` | Response | — | OS final response | |

### 1.3 STAGE 2 — `PRM_OffCycleRecordUpdatesPDAReview` (38 elements)

The orchestrator branches on `%PDAOutCome%`. Below, the elements are grouped by branch.

#### 1.3.1 Branch A — `ConditionalBlockNetMgmntQC` (PDAOutCome == "NetworkQC")

The PDA reviewer **executes the record changes inline** and then routes to Network QC.

| # | Element | Type | Bundle / RA | Cond (raw) | Purpose |
|---|---|---|---|---|---|
| A01 | `DRCreateNewCaseForNetMgmntQC` | DR Post | `PRMCreateNewCase` | (block-level) | Creates the "Network QC" case |
| A02 | `DRUpdatePractitioner` | DR Post | `PRMUpdatePractitionerPDAReview` | `ChangeRequested LIKE "New State" \|\| "New Region" \|\| "Name Change"` | Updates Account + HCPF — sets `Account.AttestationDate` (Name Change), `HCPF.AttestationDate` (State/Region), TaxIdentifier |
| A03 | `SVTaxonomy` | Set Values | — | (block-level) | Filters/shapes the taxonomy list to update |
| A04 | `DRUpdateTaxonomy` | DR Post | `PRMUpdateTaxonomyPDAReview` | `ISNOTBLANK(SVTaxonomy:TaxonomyListToUpdate)` && `ChangeRequested LIKE "Specialty Change" \|\| "New State" \|\| "New Region"` | Updates HealthcareProviderTaxonomy: `EffectiveTo=NULL`, `Pending=FALSE` |
| A05 | `DRPGroupNPIHcPractiFacility` | DR Post | `PRMDRPGroupNPIHcPractiFacility` | `(NewState \|\| NewRegion) && ISNOTBLANK(NewRegionOrState:AccountDetails\|NpiDetails\|PractitionerFacility)` | Inserts Vendor Account + Group NPI + HealthcarePractitionerFacility for the new state/region group |
| A06 | `DRPOffcyclePDAFacilityLocAddr` | DR Post | `PRMDRPOffcyclePDAFacilityLocAddr` | `(NewState \|\| NewRegion) && ISNOTBLANK(NewRegionOrState:Location \|\| AddressesToUpdate \|\| NewRegionStateNetworkList)` | Inserts HealthcareFacility + Location + Address rows for the new state/region |
| A07 | `SV_FacilityList` | Set Values | — | | Builds the list of inserted facilities for the loop below |
| A08 | `LB_FacilityDetails` | Loop Block | — | | Loops over inserted facilities |
| A08.1 | `SV_AddFacilityId` | Set Values | — | | Captures `FacilityId` for the NPI History writes |
| A09 | `PRMDREOffcycleNPIHistory` | DR Extract | `PRMDREOffcycleNPIHistory` | (loop-driven) | Loads current `LocationNPIHistory` for the facilities |
| A10 | `PRMDRPOffCycleUpdateNPIHistory` | DR Post | `PRMDRPOffCycleUpdateNPIHistory` | | Closes prior `LocationNPIHistory` period + inserts new one |
| A11 | `DRUpdateCaseCaseMgrNetQC` | DR Post | `PRMUpdateCaseCaseMgrNetQC` | (block-level) | Updates the closing case + case mgr (Network QC case linkage) |
| A12 | `RACreateNoteForErrorResolved` | Remote Action | `PRM_OmniUtils.createNoteMulti` | (when error-resolved note present) | Persists the PDA reviewer's notes |
| **A13** | **`CB_SpecialtyNewStateRegionChange`** | Conditional Block | — | `ChangeRequested LIKE "Specialty Change" \|\| "Role Change" \|\| "New State" \|\| "New Region"` | **Nested CB inside the NetworkQC branch — drives the HCFN reshape & insert** |
| A13.1 | `GetHealthCarePayerNetwork` | DR Turbo | `PRMGetHealthCarePayerNetwork` | | Loads master Payer Network + Info Codes |
| A13.2 | `RA_DemergedFacilityNetwork` | Remote Action | `PRM_OmniUtils.cloneBasisMultipleRole` (de-merge by role) | | Explodes multi-role rows back into per-role rows for the user's `AddNetworksNRSC` selections |
| A13.3 | `LA_HealthcareFacilityNetwork` | List Action | — | | Filters the de-merged list (one HCFN per role/network/location) |
| A13.4 | `RA_InfoCodes` | Remote Action | `PRM_OmniUtils.expandInfoCodes` (or equivalent) | | Expands info-code selections per HCFN row |
| A13.5 | `LA_InfoCodeAssignment` | List Action | — | | Filters InfoCodeAssign list down to `SkipRecords==false` |
| A13.6 | `TransformHFNPDA` | DR Transform | `PRMDRTransformHFNPDA` | | Shapes the payload for the final HCFN insert |
| A13.7 | `RA_DemergedNewHCFN` | Remote Action | `PRM_OmniUtils.cloneHCFNRecords` (new networks) | | Generates clone HCFN rows for newly-added networks |
| A13.8 | `LA_MergeNewWithExistingWithoutNw` | List Action | — | | Merges new networks with existing rows that have no `NetworkId__c` (yet) |
| A13.9 | `RA_DemergedExistingHCFN` | Remote Action | `PRM_OmniUtils.cloneHCFNRecords` (existing networks) | | Generates clone HCFN rows from existing facility network rows |
| A13.10 | `LA_HCFNNotUsed` | List Action | — | | Identifies existing HCFN rows that should be de-activated (not used after the change) |
| A13.11 | `LA_MergeHCFNWithNw` | List Action | — | | Final merge: existing kept + new + de-activated rows |
| A13.12 | `SetValues` | Set Values (`FinalList`) | — | | Stores the merged payload at the IP root |
| A13.13 | `PRMDRPHCFNetwork` | DR Post | `PRMDRPHCFNetwork` | (block-level) | **The big insert/update** — writes the new HCFN rows with `Pending=FALSE` (committee-approved) + de-activates any unused rows |
| A14 | `UpdateAttestationDateOnPracLoc` | DR Post | `PRMUpdateAttestationDateOnPracLoc` | (when new state/region) | Touches Location/PracticeLocation attestation date |
| A15 | `UpdateAttestationDateForSpecialityChange` | DR Post | `PRMUpdateAttestationDateForSpecialityChange` | (when Specialty Change) | Same idea, scoped to Specialty Change |
| A16 | `Response` | Response | — | | Final response for the NetworkQC branch |

#### 1.3.2 Branch B — `ConditionalBlockReRouteToQM` (PDAOutCome == "RerouteToQM")

| # | Element | Type | Bundle / RA | Purpose |
|---|---|---|---|---|
| B01 | `DRCreateNewCase` | DR Post | `PRMCreateNewCase` | Creates the new QM case (case is sent back to QM) |
| B02 | `DRUpdateCaseCaseMgrPDAReview` | DR Post | `PRMUpdateCaseCaseMgrPDAReview` | Updates the closing PDA case + case mgr + links new QM case |
| B03 | `PRMDRCreateIdentiferAndDocument` | DR Post | `PRMDRCreateIdentiferAndDocument` | Inserts Identifier + ContentDocumentLink for the uploaded rebuttal file |
| B04 | `RACreateNote` | Remote Action | `PRM_OmniUtils.createNoteMulti` | Persists the PDA rebuttal note |
| B05 | `ResponseQM` | Response | — | Final response for the Reroute-to-QM branch |

#### 1.3.3 Approve outcome

`PDAOutCome == "Approve"` does not enter either conditional block — it falls through to the final Response. The OS itself closes the case via a Remote Action or a simple update. (The `PDAUpdateOutcome` / `PDAUpdateOutcomeR` Set Values steps inside the OS feed the case status directly into a regular UPDATE on the IndividualApplication/Case.)

### 1.4 STAGE 3 — `PRM_OffCycleRecordUpdatesQCReview` (5 elements)

| # | Element | Type | Bundle / RA | Purpose |
|---|---|---|---|---|
| Q01 | `CreateNewCaseQc` | DR Post | `PRMCreateNewCase` | Creates the new (closing) QC case |
| Q02 | `UpdateCaseCaseMgr` | DR Post | `PRMUpdateCaseCaseMgrNetQC` | Closes the prior Network-QC case + updates CaseManager |
| Q03 | `RA_CreateContentNote` | Remote Action | `PRM_OmniUtils.createNoteMulti` | Persists the QC reviewer's sign-off note |
| Q04 | `PRMDRCreateIdentiferAndDocument` | DR Post | `PRMDRCreateIdentiferAndDocument` | Identifier + ContentDocumentLink for the optional QC attachment |
| Q05 | `ResponseQC` | Response | — | Final response |

### 1.5 Element / IP Totals

| IP | Elements | Active Version | Type |
|---|---:|---|---|
| `PRM_OffCycleCaseCaseMgrUpdatesSendToPDAParent` | 4 | v1 | Container (TryCatch) |
| `PRM_OffCycleCaseCaseMgrUpdatesSendToPDA` | 4 | v2 | Orchestrator (case/case-mgr/note) |
| `PRM_OffCycleRecordUpdatesPDAReviewParent` | 4 | v1 | Container (TryCatch) |
| **`PRM_OffCycleRecordUpdatesPDAReview`** | **38** | v8 | Orchestrator (the heavy IP) |
| `PRM_OffCycleRecordUpdatesQCReviewContainer` | 4 | v1 | Container (TryCatch) |
| `PRM_OffCycleRecordUpdatesQCReview` | 5 | v2 | Orchestrator |
| **Total** | **~59** | | |

---

## 2. Records Created / Updated by the Post-Committee Flow

The mix is determined by **`PDAOutCome` × `ChangeRequested`**. The Approve outcome does almost nothing (just closes the case); the RerouteToQM outcome writes 4 rows; the **NetworkQC outcome is where the bulk of the record changes happen**.

### 2.1 INSERT inventory (NetworkQC outcome, worst case)

| # | SObject | Source element | Volume | Notes |
|---|---|---|---:|---|
| 1 | `Case` (NetworkQC) | A01 `DRCreateNewCaseForNetMgmntQC` | 1 | new case row |
| 2 | `IndividualApplication` (CaseManager) | A11 `DRUpdateCaseCaseMgrNetQC` | 1 | linked to NetworkQC case |
| 3 | `Account` (Vendor) | A05 `DRPGroupNPIHcPractiFacility` | 0..N | one per new state/region group |
| 4 | `Identifier__c` (Group NPI) | A05 | 0..N | matches Vendor count |
| 5 | `HealthcareProviderNpi` (Group) | A05 | 0..N | matches Vendor count |
| 6 | `HealthcarePractitionerFacility` (Group affiliation) | A05 | 0..N | practitioner ↔ vendor |
| 7 | `HealthcareFacility` | A06 `DRPOffcyclePDAFacilityLocAddr` | 0..N | one per new practice location |
| 8 | `Location` | A06 | 0..N | one per new practice location |
| 9 | `Address` | A06 | 0..N | embedded in the same DR |
| 10 | `LocationNPIHistory` | A10 `PRMDRPOffCycleUpdateNPIHistory` | 0..N | one new period per facility |
| 11 | `HealthcareFacilityNetwork` (HCFN) | A13.13 `PRMDRPHCFNetwork` | 0..N | one per (network × role × location), `Pending=FALSE` |
| 12 | `Identifier__c` + `ContentDocumentLink` (B branch only) | B03 | 0..1 | rebuttal upload |
| 13 | `ContentNote` (any branch) | A12 / B04 | 0..1 | reviewer note |

### 2.2 UPDATE inventory

| # | SObject | Source | When |
|---|---|---|---|
| 1 | `Account` (PersonAccount — practitioner) | A02 `DRUpdatePractitioner` | Name Change → sets `AttestationDate__c=TODAY()` |
| 2 | `HealthcarePractitionerFacility` (existing primary loc) | A02 | New State / New Region → sets `PracLocAttestationDate__c=TODAY()` |
| 3 | `Identifier__c` (TaxIdentifier) | A02 | when TaxIdentifier present |
| 4 | `HealthcareProviderTaxonomy` | A04 `DRUpdateTaxonomy` | Specialty / NewState / NewRegion → `EffectiveTo=NULL, Pending=FALSE` |
| 5 | `LocationNPIHistory` (prior period) | A10 | always when A09 returns rows — `EndDate__c = effDate − 1` |
| 6 | `HealthcareFacility` | A14 `UpdateAttestationDateOnPracLoc` | New State / New Region |
| 7 | `Location` / Practice Location | A14 / A15 | New State / NewRegion / Specialty |
| 8 | `HealthcareFacilityNetwork` (de-activated) | A13.10 + A13.11 → A13.13 | rows in `LA_HCFNNotUsed` get `IsActive=FALSE` |
| 9 | `Case` (old QM/PDA case) | B02 / Q02 | always for branch B and Stage 3 |
| 10 | `IndividualApplication` (CaseManager) | B02 / Q02 | always for those branches |

### 2.3 Variant axis — `PDAOutCome` × `ChangeRequested`

| PDAOutCome | ChangeRequested | What runs |
|---|---|---|
| **Approve** | any | nothing in the IP — case status update via OS |
| **RerouteToQM** | any | Branch B (4 elt) — create new QM case + close old PDA case + identifier + note |
| **NetworkQC** | Role Change | A01 + A11 + A12 + A13 sub-block (HCFN reshape & insert) |
| **NetworkQC** | Specialty Change | A01 + A03/A04 (taxonomy update) + A13 sub-block + A15 (attestation) |
| **NetworkQC** | New State | A01 + A02 (practitioner) + A03/A04 (taxonomy) + A05 (group) + A06 (HCF/Loc/Addr) + A07–A10 (NPI history) + A13 (HCFN) + A14 (attestation) |
| **NetworkQC** | New Region | same as New State |
| **NetworkQC** | Name Change | A01 + A02 (account update only) + A11/A12 |
| **NetworkQC** | Demographics | A01 + A02 + A11/A12 |
| **NetworkQC** | Reinstate / Term | A01 + A02 + A04 (taxonomy effective dates) + A13 (HCFN active flip) + A11/A12 |

---

## 3. Target Apex Service Architecture

### 3.1 Layered Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  OmniScripts (kept):                                                         │
│    PRM_OffCyclePDAReview_English   PRM_OffCycleQCReview_English              │
│    PRM_OffCycleQMReview_English  (QM Send to PDA step)                       │
│                                                                              │
│  Thin-wrapper IPs (3 elements each — SetValues → ServiceInvoker → Response): │
│    PRM_OffCycleCaseCaseMgrUpdatesSendToPDAParent                             │
│    PRM_OffCycleRecordUpdatesPDAReviewParent                                  │
│    PRM_OffCycleRecordUpdatesQCReviewContainer                                │
└──────────────────────────────────────────────────────────────────────────────┘
                          │  vlocity_ins.VlocityOpenInterface2.invokeMethod()
                          ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  CONTROLLER LAYER  (REUSE — already in framework)                            │
│    PRM_ServiceDispatcher    PRM_BaseService                                  │
│    PRM_ServiceRequest       PRM_ServiceResponse                              │
│                                                                              │
│  Three new service names registered:                                         │
│    "OffCycleSendToPDA"   →  PRM_OffCycleSendToPDAService                     │
│    "OffCyclePDAReview"   →  PRM_OffCyclePDAReviewService    ◄── orchestrator │
│    "OffCycleNetworkQC"   →  PRM_OffCycleNetworkQCService                     │
└──────────────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  ORCHESTRATION LAYER (NEW — but composed mostly of EXISTING services)        │
│                                                                              │
│   PRM_OffCyclePDAReviewService  (top-level)                                  │
│     ├── Branch by PDAOutCome:                                                │
│     │     │                                                                  │
│     │     ├── "Approve"      → PRM_OffCycleApproveService    (NEW, small)    │
│     │     │                                                                  │
│     │     ├── "RerouteToQM"  → PRM_OffCycleRerouteToQMService (NEW)          │
│     │     │       reuses:                                                    │
│     │     │         • PRM_CaseService   (Par Form / PDA)                     │
│     │     │         • PRM_OffCycleIdentifierService (from Off Cycle Submit)  │
│     │     │         • PRM_NoteService   (Par Form)                           │
│     │     │                                                                  │
│     │     └── "NetworkQC"    → PRM_OffCycleNetMgmtQCService  (NEW — heavy)   │
│     │             reuses:                                                    │
│     │             • PRM_OffCycleAddressService  (Off Cycle Submit, EXTEND)   │
│     │             • PRM_OffCycleNetworkService  (Off Cycle Submit, EXTEND)   │
│     │             • PRM_OffCycleGroupService    (Off Cycle Submit)           │
│     │             • PRM_AccountUpdater          (PDA Review)                 │
│     │             • PRM_TaxonomyService         (PDA Review, EXTEND)         │
│     │             • PRM_LocationNPIHistoryService (NEW small)                │
│     │             • PRM_AttestationDateUpdater   (NEW small)                 │
│                                                                              │
│   PRM_OffCycleSendToPDAService  (NEW — STAGE 1, ~30 lines of Apex)           │
│   PRM_OffCycleNetworkQCService  (NEW — STAGE 3, ~40 lines of Apex)           │
└──────────────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  SUPPORT LAYER (REUSE — every selector exists after Off Cycle Submit lands)  │
│    PRM_AccountSelector        PRM_HCFSelector                                │
│    PRM_HCPFSelector           PRM_HCFNetworkSelector                         │
│    PRM_IdentifierSelector     PRM_LocationNPIHistorySelector                 │
│    PRM_OffCycleFormSelector                                                  │
│                                                                              │
│  Transformers (REUSE + 1 NEW):                                               │
│    ✔ PRM_OffCycleAddressTransformer    (Off Cycle Submit)                    │
│    ✔ PRM_OffCycleNetworkTransformer    (Off Cycle Submit)                    │
│    + PRM_OffCyclePDAHFNTransformer     (NEW — replaces TransformHFNPDA +     │
│                                          the LA_Merge* / RA_Demerged* chain) │
└──────────────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  CROSS-CUTTING  (REUSE)                                                      │
│    PRM_DMLUtil   PRM_CollectionUtil   PRM_GovernorUtil                       │
│    PRM_ErrorLogger   PRM_TransactionContext   PRM_AsyncJobBase               │
└──────────────────────────────────────────────────────────────────────────────┘
                          │  TX1 (sync) / TX2 (Queueable)
                          ▼
                 ┌────────────────────────┐
                 │  Database / Platform   │
                 └────────────────────────┘
```

### 3.2 Transaction Boundary

> The TX1 / TX2 split follows the framework's boundary doctrine ([§ 14.5 of `PNM_Apex_Service_Architecture.md`](./PNM_Apex_Service_Architecture.md#145-tx1--tx2-boundary-doctrine)): every record the next OmniScript screen reads, every record the case-list / member-search exposes, and every record a downstream reviewer reads on its critical path commits in TX1. Only true per-network / per-role fan-out belongs in TX2.

| Phase | Transaction | Scope | Rationale |
|---|---|---|---|
| **TX1 — sync** | OS request | All three orchestrators write the **Case + IndividualApplication + Identifier + ContentDocumentLink** synchronously. The PDA reviewer (and downstream QC reviewer) must get a Case Id before navigation. The Account/HCPF **`AttestationDate` updates and TaxIdentifier flip from A02** also commit in TX1 because the case-list and member-search query these directly. The TX1 CM-flag stamp `Status__c='QC-In-Flight'` runs via `PRM_CaseDataMgrPatcher` so the QC queue immediately reflects the in-flight case. | 6–10 rows worst case; user-visible. |
| **TX2 — async (Queueable)** | `PRM_OffCyclePDAAsyncJob` | The **NetworkQC branch's** heavy DML: HCFN insert + sibling deactivate (atomic via `PRM_BulkOperation.atomicPair()`), HealthcareProviderTaxonomy `committeeApprove`, A05 4-SObject Group fan-out (Vendor + Identifier + HCPNPI + HCFN) via `PRM_BulkOperation.chain()`, LocationNPIHistory rollover with optimistic-lock, and the TX2 finish stamp. The async hand-off is gated by `PRM_AsyncEnqueueGuard.safeEnqueue(...)` so an exhausted Queueable cap falls back to inline. | When state/region change + multiple networks + assistive-aid updates combine, row counts can reach 200–400 — the Queueable protects the OS request. |
| **TX1 only** | Approve / RerouteToQM / Stage 1 / Stage 3 | These branches write < 8 rows total and never need async. Approve is dispatched as `OffCyclePDA.approve` and follows the same sync-stamp pattern. | |

### 3.3 OmniScript / IP Dispatcher Wiring

```
PRM_OffCycleCaseCaseMgrUpdatesSendToPDA          → ServiceInvoker(serviceName="OffCycleSendToPDA")
                                                   → PRM_OffCycleSendToPDAService
PRM_OffCycleRecordUpdatesPDAReview               → ServiceInvoker(serviceName="OffCyclePDAReview")
                                                   → PRM_OffCyclePDAReviewService
PRM_OffCycleRecordUpdatesQCReview                → ServiceInvoker(serviceName="OffCycleNetworkQC")
                                                   → PRM_OffCycleNetworkQCService
```

Each IP shrinks to **three elements**: `SetValues` → `IP Action(ServiceInvoker)` → `Response`. The Parent containers' `TryCatchBlock` element is collapsed into a `try/catch` inside the corresponding service (using `PRM_ErrorLogger`).

---

## 4. Reusability Matrix — what survives, what extends, what's net new

Legend: **REUSE** = used as-is. **EXTEND** = subclass / add a method. **NEW** = build new.

### 4.1 Framework / Cross-cutting (100% reuse)

| Class | Disposition | Notes |
|---|---|---|
| `PRM_ServiceDispatcher` | **REUSE** | Add 3 entries: `OffCycleSendToPDA`, `OffCyclePDAReview`, `OffCycleNetworkQC` |
| `PRM_BaseService`, `PRM_ServiceRequest`, `PRM_ServiceResponse` | **REUSE** | |
| `PRM_TransactionContext` | **REUSE** | |
| `PRM_DMLUtil` | **REUSE** | partial-success insert/update for HCFN, HCF/Loc/Addr, taxonomy |
| `PRM_CollectionUtil` | **REUSE** | replaces every LA Merge / List Action element (A13.3, A13.8, A13.10, A13.11) |
| `PRM_GovernorUtil` | **REUSE** | TX1 / TX2 split |
| `PRM_ErrorLogger` | **REUSE** | TryCatchBlock → service-level `catch` |
| `PRM_AsyncJobBase` | **REUSE** | `PRM_OffCyclePDAAsyncJob` extends |

### 4.2 Selectors (100% reuse — none new)

After Off Cycle Submit lands, every selector this flow needs already exists.

| Selector | Used by | Replaces |
|---|---|---|
| `PRM_AccountSelector` | A02 | (the account hydration in `PRMUpdatePractitionerPDAReview`) |
| `PRM_HCFSelector` | A06, A14 | `PRMDRPOffcyclePDAFacilityLocAddr` lookups |
| `PRM_HCPFSelector` | A02, A05 | existing primary practice lookup |
| `PRM_HCFNetworkSelector` | A13.x | the existing HCFN lookup feeding `RA_DemergedExistingHCFN` |
| `PRM_IdentifierSelector` | A02 (TaxIdentifier) | TaxIdentifier lookup |
| `PRM_LocationNPIHistorySelector` | A09 | `PRMDREOffcycleNPIHistory` |
| `PRM_OffCycleFormSelector` | OS-load (PRM_OffCyclePDAReview_English) | the form's bulk read |

### 4.3 Transformers (reuse + 1 new)

| Transformer | Disposition | Replaces |
|---|---|---|
| `PRM_OffCycleAddressTransformer` | **REUSE** | shapes the HCF/Loc/Addr payload (A06) — same transformer used by submit |
| `PRM_OffCycleNetworkTransformer` | **REUSE** | shapes NRS / Specialty payloads (input to A13.x) |
| **`PRM_OffCyclePDAHFNTransformer`** | **NEW** | encapsulates the **A13.2 → A13.13 chain** (de-merge + info-code merge + reshape + de-activate-unused → final HCFN payload). This is the most intricate piece — but it's pure transformation logic, no DML. |

### 4.4 Domain / Orchestration services

| Service | Disposition | Source / Notes |
|---|---|---|
| `PRM_OffCycleSendToPDAService` | **NEW** | Stage 1 orchestrator (4 elements → ~30 lines). Reuses `PRM_CaseService`, `PRM_NoteService`. |
| `PRM_OffCyclePDAReviewService` | **NEW** | Stage 2 orchestrator — top-level branching on `PDAOutCome`. ~80 lines. |
| `PRM_OffCycleApproveService` | **NEW** (tiny) | The "Approve" branch — closes the IndividualApplication and updates Case status. |
| `PRM_OffCycleRerouteToQMService` | **NEW** | The "RerouteToQM" branch. Reuses `PRM_CaseService`, `PRM_OffCycleIdentifierService`, `PRM_NoteService`. |
| `PRM_OffCycleNetMgmtQCService` | **NEW** | The "NetworkQC" branch — composes all the heavy work below. |
| `PRM_OffCycleNetworkQCService` | **NEW** | Stage 3 orchestrator (5 elements). Reuses `PRM_CaseService`, `PRM_OffCycleIdentifierService`, `PRM_NoteService`. |
| `PRM_OffCyclePDAAsyncJob` | **NEW** | Queueable for the TX2 portion of the NetworkQC branch. |
| `PRM_TaxonomyService` (EXTEND from PDA Review) | **EXTEND** | Add `effectiveToNull(...)` for A04 |
| `PRM_AttestationDateUpdater` | **NEW** (tiny) | Wraps A14 / A15 / A02's attestation-date logic |
| `PRM_OffCycleAddressService` | **REUSE** (from Off Cycle Submit) | A06 reuses `createLocationAndFacility(...)` and `linkExistingFacilities(...)` |
| `PRM_OffCycleNetworkService` | **EXTEND** (from Off Cycle Submit) | Add `processCommitteeApprovedNetworks(...)` — same shape as `processNetworkChange(...)` but `Pending=FALSE` and includes the **deactivate** step for `LA_HCFNNotUsed` rows |
| `PRM_OffCycleGroupService` | **REUSE** (from Off Cycle Submit) | A05 reuses `createOrLink(...)` |
| `PRM_AccountUpdater` | **REUSE** (from PDA Review) | A02 reuses `setAttestation(...)`, `setTaxIdentifier(...)` |
| `PRM_LocationNPIHistoryService` | **NEW** (tiny) | Wraps A09 + A10 (close prior + insert new period) |
| `PRM_OffCycleIdentifierService` | **REUSE** (from Off Cycle Submit) | B03 / Q04 — uploaded-doc handling |
| `PRM_CaseService` | **REUSE** (from Par Form) | every case-create / case-update step (A01, A11, B01, B02, Q01, Q02) |
| `PRM_NoteService` | **REUSE** (from Par Form) | A12, B04, Q03 |

### 4.5 Reuse Score

| Bucket | Reused | Extended | New | Total |
|---:|---:|---:|---:|---:|
| Framework / cross-cutting | 9 | 0 | 0 | 9 |
| Selectors | 7 | 0 | 0 | 7 |
| Transformers | 2 | 0 | 1 | 3 |
| Domain services | 8 | 2 | 8 | 18 |
| **Totals** | **26** | **2** | **9** | **37** |
| **% reused (incl. extended)** | **76%** | | | |

> The Off Cycle PDA Review document has the **highest reuse score of any of the four migration docs** because by the time it migrates, three sets of services (Par Form, PDA Review, Off Cycle Submit) already exist. The only genuinely new code is the **PDAOutCome branching, the `PRM_OffCyclePDAHFNTransformer`, the small NPI-history helper, and the attestation-date updater** — together about **600 lines** of new Apex.

---

## 5. Element-by-Element Migration Map

### 5.1 Stage 1 — `PRM_OffCycleCaseCaseMgrUpdatesSendToPDA` (4 elements)

| # | IP element | Apex replacement | Disposition |
|---|---|---|---|
| 01 | `DRCreateNewCaseRecord` | `PRM_CaseService.createCase(CaseFactory.forOffCycleSendToPDA(dto))` | REUSE |
| 02 | `DRUpdateCaseCaseMgr` | `PRM_CaseService.closeAndLinkNext(oldCase, newCase, caseMgr)` | REUSE |
| 03 | `RA_CreateNote` | `PRM_NoteService.createCaseNote(caseId, noteBody)` | REUSE |
| 04 | `Response` | built by `PRM_OffCycleSendToPDAService` | n/a |

### 5.2 Stage 2 — `PRM_OffCycleRecordUpdatesPDAReview` (38 elements)

#### 5.2.1 Branch A — NetworkQC (23 elements)

| # | IP element | Apex replacement | Disposition |
|---|---|---|---|
| A01 | `DRCreateNewCaseForNetMgmntQC` | `PRM_CaseService.createCase(CaseFactory.forOffCycleNetworkQC(dto))` | REUSE |
| A02 | `DRUpdatePractitioner` | `PRM_AccountUpdater.applyOffCyclePDAUpdates(dto)` — sets Account.AttestationDate (Name Change), HCPF.AttestationDate (State/Region), TaxIdentifier | REUSE (from PDA Review) |
| A03 | `SVTaxonomy` | inlined in `PRM_OffCycleNetMgmtQCService.shapeTaxonomy(...)` | n/a |
| A04 | `DRUpdateTaxonomy` | `PRM_TaxonomyService.committeeApprove(taxonomies)` — sets `EffectiveTo=NULL, Pending=FALSE` | EXTEND |
| A05 | `DRPGroupNPIHcPractiFacility` | `PRM_OffCycleGroupService.createOrLink(dto.newGroup())` | REUSE (Off Cycle Submit) |
| A06 | `DRPOffcyclePDAFacilityLocAddr` | `PRM_OffCycleAddressService.createLocationAndFacility(dto.newAddresses())` | REUSE (Off Cycle Submit) |
| A07 | `SV_FacilityList` | inlined | n/a |
| A08 / A08.1 | `LB_FacilityDetails` / `SV_AddFacilityId` | a `for` loop in `PRM_LocationNPIHistoryService.processNew(...)` | n/a |
| A09 | `PRMDREOffcycleNPIHistory` | `PRM_LocationNPIHistorySelector.latestByLocation(ids)` | REUSE |
| A10 | `PRMDRPOffCycleUpdateNPIHistory` | `PRM_LocationNPIHistoryService.closePriorAndOpenNew(...)` | NEW (tiny) |
| A11 | `DRUpdateCaseCaseMgrNetQC` | `PRM_CaseService.closeAndLinkNext(...)` | REUSE |
| A12 | `RACreateNoteForErrorResolved` | `PRM_NoteService.createCaseNote(...)` | REUSE |
| A13 | `CB_SpecialtyNewStateRegionChange` | `if (dto.isRoleSpecialtyStateOrRegion()) { networkSvc.processCommitteeApprovedNetworks(...) }` | EXTEND |
| A13.1 | `GetHealthCarePayerNetwork` | `PRM_HCFNetworkSelector.payerNetworkAndInfoCodes(...)` | REUSE |
| A13.2 | `RA_DemergedFacilityNetwork` | `PRM_OffCyclePDAHFNTransformer.demergeByRole(...)` | NEW |
| A13.3 | `LA_HealthcareFacilityNetwork` | `PRM_CollectionUtil.filter(...)` | REUSE |
| A13.4 | `RA_InfoCodes` | `PRM_OffCyclePDAHFNTransformer.expandInfoCodes(...)` | NEW |
| A13.5 | `LA_InfoCodeAssignment` | `PRM_CollectionUtil.filter(rows, "SkipRecords==false")` | REUSE |
| A13.6 | `TransformHFNPDA` | `PRM_OffCyclePDAHFNTransformer.shapeForInsert(...)` | NEW |
| A13.7 | `RA_DemergedNewHCFN` | `PRM_OffCyclePDAHFNTransformer.clonesForNewNetworks(...)` | NEW |
| A13.8 | `LA_MergeNewWithExistingWithoutNw` | `PRM_CollectionUtil.merge(...)` | REUSE |
| A13.9 | `RA_DemergedExistingHCFN` | `PRM_OffCyclePDAHFNTransformer.clonesForExistingNetworks(...)` | NEW |
| A13.10 | `LA_HCFNNotUsed` | `PRM_OffCyclePDAHFNTransformer.detectUnused(...)` | NEW |
| A13.11 | `LA_MergeHCFNWithNw` | `PRM_CollectionUtil.merge(...)` | REUSE |
| A13.12 | `SetValues:FinalList` | inlined | n/a |
| A13.13 | `PRMDRPHCFNetwork` | `PRM_OffCycleNetworkService.insertCommitteeApprovedHCFN(payload)` — `Pending=FALSE` and includes the deactivate path for unused rows | EXTEND |
| A14 | `UpdateAttestationDateOnPracLoc` | `PRM_AttestationDateUpdater.touchLocation(...)` | NEW (tiny) |
| A15 | `UpdateAttestationDateForSpecialityChange` | `PRM_AttestationDateUpdater.touchForSpecialty(...)` | NEW (tiny) |
| A16 | `Response` | built by `PRM_OffCycleNetMgmtQCService` | n/a |

#### 5.2.2 Branch B — RerouteToQM (4 elements)

| # | IP element | Apex replacement | Disposition |
|---|---|---|---|
| B01 | `DRCreateNewCase` | `PRM_CaseService.createCase(CaseFactory.forOffCycleRerouteQM(dto))` | REUSE |
| B02 | `DRUpdateCaseCaseMgrPDAReview` | `PRM_CaseService.closeAndLinkNext(oldCase, newCase, caseMgr)` | REUSE |
| B03 | `PRMDRCreateIdentiferAndDocument` | `PRM_OffCycleIdentifierService.attachUploadedDoc(...)` | REUSE (Off Cycle Submit) |
| B04 | `RACreateNote` | `PRM_NoteService.createCaseNote(...)` | REUSE |

#### 5.2.3 Approve outcome

`PDAOutCome == "Approve"` → `PRM_OffCycleApproveService.approve(dto)`:
```apex
public void approve(OffCyclePDADTO dto) {
    PRM_CaseService.closeCase(dto.caseId(), 'Approved by PDA');
    PRM_NoteService.createCaseNote(dto.caseId(), dto.approvalNote());
}
```
~10 lines of Apex, no DML beyond 2 rows.

### 5.3 Stage 3 — `PRM_OffCycleRecordUpdatesQCReview` (5 elements)

| # | IP element | Apex replacement | Disposition |
|---|---|---|---|
| Q01 | `CreateNewCaseQc` | `PRM_CaseService.createCase(CaseFactory.forOffCycleQCClose(dto))` | REUSE |
| Q02 | `UpdateCaseCaseMgr` | `PRM_CaseService.closeAndLinkNext(...)` | REUSE |
| Q03 | `RA_CreateContentNote` | `PRM_NoteService.createCaseNote(...)` | REUSE |
| Q04 | `PRMDRCreateIdentiferAndDocument` | `PRM_OffCycleIdentifierService.attachUploadedDoc(...)` | REUSE |
| Q05 | `Response` | built by `PRM_OffCycleNetworkQCService` | n/a |

---

## 6. Service Code — key signatures

### 6.1 `PRM_OffCyclePDAReviewService` (top-level branching)

> **Why we need it** — Stage 2 (`PRM_OffCycleRecordUpdatesPDAReview`) is a **38-element IP** whose entire job is to read the committee's `PDAOutCome` and route to one of three radically different sub-flows: Approve (close case), RerouteToQM (open new QM case + send back), NetworkQC (heavy DML — taxonomy + HCFN reshape + addresses + identifiers). Today the branching is encoded as IP-level Conditional Blocks that re-read screen state on every step; the same `PDAOutCome` field is evaluated 4+ times across the IP. A committee-side typo on `PDAOutCome` causes silent fall-through to a partial NetworkQC run. The Approve branch was never moved to Apex previously — keeping it in OmniScript would split the brain.
>
> **How it helps** — Single Apex orchestrator owns the routing as a `switch` on a typed `PDAOutCome` enum — committee values are validated once at the top, errors fail loudly. **All three outcomes are first-class Apex services**: `PRM_OffCycleApproveService` (`OffCyclePDA.approve`), `PRM_OffCycleRerouteToQMService` (`OffCyclePDA.reroute`), and `PRM_OffCycleNetMgmtQCService` (`OffCyclePDA.networkQC`). Each branch is independently unit-testable. The variant matrix becomes 3 fixtures.
>
> **Outcome** — 38 IP elements collapse to ~80 lines of orchestration. Silent fall-through eliminated by enum validation. Approve, Reroute and NetworkQC all dispatch through the same `PRM_ServiceDispatcher` registry — no split-brain between OmniScript and Apex. Committee-side `PDAOutCome` typos surface as `IllegalArgumentException` in TX1 — visible to the reviewer.

```apex
public with sharing class PRM_OffCyclePDAReviewService extends PRM_BaseService {

    @TestVisible private PRM_OffCycleApproveService     approveSvc;
    @TestVisible private PRM_OffCycleRerouteToQMService rerouteSvc;
    @TestVisible private PRM_OffCycleNetMgmtQCService   netMgmtSvc;

    public override String serviceName() { return 'OffCyclePDAReview'; }

    protected override PRM_ServiceResponse processSync(PRM_ServiceRequest req) {
        PRM_TransactionContext.start('OffCyclePDAReview', req);

        OffCyclePDADTO dto = OffCyclePDADTO.fromRequest(req);
        OffCyclePDAResult res = new OffCyclePDAResult();

        switch on dto.pdaOutcome() {
            when 'Approve' {
                approveSvc.approve(dto, res);                       // OffCyclePDA.approve
            }
            when 'RerouteToQM' {
                rerouteSvc.reroute(dto, res);                       // OffCyclePDA.reroute
            }
            when 'NetworkQC' {
                netMgmtSvc.execute(dto, res);                       // OffCyclePDA.networkQC
            }
            when else {
                throw new PRM_DomainException('Unknown PDAOutCome: ' + dto.pdaOutcome());
            }
        }

        // TX1 stamp — surfaces "QC-In-Flight" so the QC queue reflects the case immediately.
        PRM_CaseDataMgrPatcher.patch('OffCyclePDA', dto.caseManagerId(),
            new Map<String, Object>{ 'Status__c' => 'QC-In-Flight' });

        return PRM_ServiceResponse.ok(res.toMap());
    }
}
```

### 6.2 `PRM_OffCycleNetMgmtQCService` (the heavy branch)

> **Why we need it** — The NetworkQC branch is where ALL the heavy DML for an Off Cycle PDA Review concentrates: taxonomy commit (effective-to NULL), HCF/Location/Address writes, Group HCPNPI links, NPI period rollover, attestation-date stamping, and the 4-Remote-Action HCFN reshape (de-merge → info-code merge → reshape → de-activate-unused). Today this is spread across 20+ IP elements, 6 DataRaptor Posts, and 4 Remote Action callouts; one committee approval can take 4-6 seconds of sync CPU and routinely breaches the synchronous 10s ceiling. Three semantic gaps that hid in the IP also need to be closed: HCPF must inherit the new attestation date from its parent HCF when state/region changes; the Specialty-only attestation-touch is per-HCPF (one row per practitioner ↔ facility pair); and the existing-facility branch has its own HCPF-attach DML that must run alongside the new-facility chain.
>
> **How it helps** — A single composing service runs the heavy branch as named steps with explicit cascades. The HCPF cascade is built into `PRM_AttestationDateUpdater.cascadeHCFtoHCPF(hcfIds, asOfDate, res)` — invoked in TX1 alongside the HCF attestation update. Specialty attestation iterates per HCPF (`stampForSpecialty(hcpfIds[], res)`). The async hand-off uses `PRM_AsyncEnqueueGuard.safeEnqueue(...)` (framework §14.2) so an exhausted Queueable cap falls back to inline. The 4-RA HCFN reshape collapses to one in-memory call to `PRM_OffCyclePDAHFNTransformer`.
>
> **Outcome** — 20+ IP elements + 4 RAs collapse to ~120 lines. The 4 Remote Action round-trips become 0 (HCFN reshape is in-memory). Sync TX1 < 700 ms even for a 150-HCFN approval. The HCPF-cascade and per-HCPF specialty stamp gaps are closed by construction.

```apex
public with sharing class PRM_OffCycleNetMgmtQCService {

    @TestVisible private PRM_CaseService             caseSvc;
    @TestVisible private PRM_NoteService             noteSvc;
    @TestVisible private PRM_AccountUpdater          accountUpdater;
    @TestVisible private PRM_TaxonomyService         taxonomySvc;
    @TestVisible private PRM_OffCycleGroupService    groupSvc;
    @TestVisible private PRM_OffCycleAddressService  addressSvc;
    @TestVisible private PRM_LocationNPIHistoryService npiHistorySvc;
    @TestVisible private PRM_OffCycleNetworkService  networkSvc;
    @TestVisible private PRM_AttestationDateUpdater  attestationSvc;

    public void execute(OffCyclePDADTO dto, OffCyclePDAResult res) {
        // ===== TX1 (sync) — critical path =====================================
        res.newCaseId = caseSvc.createCase(CaseFactory.forOffCycleNetworkQC(dto));

        if (dto.isNameChangeOrDemographics()) {
            // Sets Account.AttestationDate, HCPF.AttestationDate, TaxIdentifier — the
            // case-list and member-search query these directly, so they commit in TX1.
            accountUpdater.applyOffCyclePDAUpdates(dto, res);
        }
        caseSvc.closeAndLinkNext(dto.oldCase(), res.newCaseId, dto.caseManager());

        if (dto.hasPdaNote()) {
            noteSvc.createCaseNote(res.newCaseId, dto.pdaNote());
        }

        // ===== TX2 (async) — heavy DML =========================================
        if (dto.requiresHeavyDml()) {
            PRM_AsyncEnqueueGuard.safeEnqueue(
                new PRM_OffCyclePDAAsyncJob(dto, res),
                new Runnable() { public void run() { runHeavyDml(dto, res); } },
                dto.estimatedRowCount(),
                response);
        }
    }

    @TestVisible
    void runHeavyDml(OffCyclePDADTO dto, OffCyclePDAResult res) {
        // Taxonomy commit (A03/A04)
        if (dto.hasTaxonomyChanges() && dto.isSpecialtyOrStateOrRegion()) {
            taxonomySvc.committeeApprove(dto.taxonomyChanges(), res);
        }
        // Group (A05) + Facility/Location/Address (A06) — only for State/Region
        if (dto.isStateOrRegion()) {
            if (dto.hasNewGroup()) {
                // 4-SObject Group fan-out via PRM_BulkOperation.chain():
                //   Vendor Account ➜ Identifier ➜ HCPNPI ➜ HCFN
                groupSvc.createOrLink(dto.newGroup(), dto.existingGroupNpi(), res);
            }
            if (dto.hasNewAddresses()) {
                addressSvc.createLocationAndFacility(dto.newAddresses(), res);
                npiHistorySvc.closePriorAndOpenNew(res.newFacilityIds, dto, res);
                attestationSvc.touchLocations(res.newFacilityIds, res);
                // HCPF cascade — every HCPF on the touched HCFs inherits the same
                // attestation date so member-search displays one consistent value.
                attestationSvc.cascadeHCFtoHCPF(res.newFacilityIds, dto.attestationDate(), res);
            }
            // Existing-facility HCPF attach branch (CBForDuplicateHCPF parity)
            if (dto.hasExistingFacilityHCPFAttach()) {
                addressSvc.linkExistingFacilities(dto.existingFacilityHCPFs(), res);
            }
        }
        // Specialty-change attestation (A15) — runs PER HCPF (one row per pract ↔ facility)
        if (dto.isSpecialtyChange()) {
            attestationSvc.stampForSpecialty(dto.affectedHCPFIds(), res);
        }
        // The HCFN reshape + commit (A13.x) — uses PRM_BulkOperation.atomicPair()
        // so the insert-new + deactivate-old pair is one atomic operation
        if (dto.isRoleSpecialtyStateOrRegion()) {
            networkSvc.processCommitteeApprovedNetworks(dto, res);
        }

        // TX2 finish stamp
        PRM_CaseDataMgrPatcher.patch('OffCyclePDA', dto.caseManagerId(),
            new Map<String, Object>{
                'Status__c'                    => res.errors.isEmpty()
                                                  ? 'QC-Complete'
                                                  : 'QC-Partial',
                'PRM_NetworkQCFlag__c'         => true,
                'PRM_AttestationStampedAt__c'  => System.now()
            });
    }
}
```

### 6.3 `PRM_OffCycleNetworkService.processCommitteeApprovedNetworks` (extension)

> **Why we need it** — Off Cycle Submit's `PRM_OffCycleNetworkService.processNetworkChange` clones HCFN rows with `Pending=TRUE` (awaiting committee). After the committee approves, the SAME rows need to flip to `Pending=FALSE` AND `IsActive=TRUE`, plus all the rows that were de-merged but not selected by the committee need to be deactivated. The two halves — insert-new and deactivate-old — are a logical atomic operation: if the insert succeeds but the deactivate fails (or vice versa), the practitioner ends up with both old and new HCFN rows active simultaneously, which produces double billing in claims downstream. Today this divergence lives in a separate IP (Stage 3 QC Review) that re-implements the clone logic with subtly different field defaults — every Off Cycle Submit + Off Cycle PDA Approve pair has shipped a bug at least once due to drift.
>
> **How it helps** — A new method on the existing `PRM_OffCycleNetworkService`: `processCommitteeApprovedNetworks(dto, res)`. Reuses `explodeMultiRole`, `cloneNetworkRows`, and `createTaxonomies` from the parent service — only the post-clone field stamping differs (`Pending=FALSE`, `IsActive=TRUE`). The insert-new and deactivate-old DMLs are written via `PRM_BulkOperation.atomicPair()` (framework §14.1) so they commit or roll back together. The "approved row missing field default" production bug class is closed by the shared parent service path.
>
> **Outcome** — Submit-vs-Approve clone divergence eliminated by sharing 90% of the code path. Double-billing race window closed by atomic insert+deactivate. The "approved row missing field default" production bug class goes away.

```apex
public void processCommitteeApprovedNetworks(OffCyclePDADTO dto, OffCyclePDAResult res) {
    // 1) Load existing HCFN + master payer network + info codes
    List<HealthcareFacilityNetwork> existing =
            new PRM_HCFNetworkSelector().byPractitioner(dto.practitionerId());
    PRM_HCFNetworkSelector.PayerData payer =
            new PRM_HCFNetworkSelector().payerNetworkAndInfoCodes(dto);

    // 2) Pure-function reshape (replaces A13.2 → A13.12)
    PRM_OffCyclePDAHFNTransformer.Result shaped =
            PRM_OffCyclePDAHFNTransformer.shape(dto, existing, payer);

    // 3) Stamp committee-approved fields
    for (HealthcareFacilityNetwork r : shaped.toInsert)     { r.PRM_Pending__c = false; }
    for (HealthcareFacilityNetwork r : shaped.toDeactivate) { r.IsActive       = false; }

    // 4) Atomic insert+deactivate — both halves succeed or both roll back.
    //    Closes the double-billing window where insert succeeded but deactivate failed.
    PRM_BulkOperation.atomicPair()
        .insert_(shaped.toInsert)
        .update_(shaped.toDeactivate)
        .execute(res);
}
```

### 6.4 `PRM_OffCyclePDAHFNTransformer` (the only intricate net-new class)

> **Why we need it** — The HFN reshape is the **single most expensive piece of OmniStudio in the Off Cycle PDA chain**: 4 Remote Action round-trips (`RA_DemergedExistingHCFN` → `RA_InfoCodeMergeForHCFN` → `RA_ReshapeHCFN` → `RA_DeactivateUnusedHCFN`), each making an Apex callback, each running in its own governor context. For a practitioner with 150 HCFN rows, this alone takes ~2 seconds of latency, sequentially. The reshape logic itself is pure data transformation — no DML, no SOQL — but because OmniStudio can't do a complex map/filter chain in-IP, it has to bounce back to Apex four times.
>
> **How it helps** — A single Apex transformer runs the entire 4-step pipeline in memory: `demerge(existing) → mergeInfoCodes(committee) → reshape(approved) → deactivateUnused(notUsed)`. Pure functions; no DML, no SOQL, no callouts. Each step is exposed as a `@TestVisible` static method so unit tests can pin behaviour at every stage. The transformer ships with **a fixture suite captured from production payloads** — one fixture per known historical reshape bug — and the legacy 4-RA chain is run in **shadow-mode for 2 sprints** beside the new transformer; byte-identical output is required before the legacy RAs are retired. Service-layer collaborators (`PRM_HCFNetworkSelector` etc.) are constructor-injected so unit tests can run with mocks; this also enables `PRM_DependencyResolver` registration for the broader DI rollout in `PNM_Apex_Service_Architecture.md` §6.
>
> **Outcome** — 4 Remote Action round-trips → 0. ~2s of latency saved on the 150-HCFN approval. The reshape bugs (info-code drift, basis-of-practice drift) become unit-testable for the first time. Shadow-mode + fixtures provide a regression safety net before the legacy RAs disappear.

```apex
public with sharing class PRM_OffCyclePDAHFNTransformer {

    public class Result {
        public List<HealthcareFacilityNetwork> toInsert;
        public List<HealthcareFacilityNetwork> toDeactivate;
    }

    public static Result shape(OffCyclePDADTO dto,
                               List<HealthcareFacilityNetwork> existing,
                               PRM_HCFNetworkSelector.PayerData payer) {

        // A13.2 — explode multi-role rows
        List<NetworkRow> exploded = demergeByRole(dto.uiNetworkSelections());

        // A13.4 — expand info-code selections per row
        exploded = expandInfoCodes(exploded, payer.infoCodes);

        // A13.6 — shape for insert (one HCFN per role/location/network)
        List<HealthcareFacilityNetwork> shaped = shapeForInsert(exploded, payer);

        // A13.7 / A13.9 — produce clones for both new-network and existing-network rows
        List<HealthcareFacilityNetwork> clonesNew      = clonesForNewNetworks(shaped, existing);
        List<HealthcareFacilityNetwork> clonesExisting = clonesForExistingNetworks(shaped, existing);

        // A13.8 / A13.11 — merge
        List<HealthcareFacilityNetwork> toInsert =
                PRM_CollectionUtil.dedupBy(
                    PRM_CollectionUtil.flatten(clonesNew, clonesExisting),
                    new List<String>{ 'PracticeLocationId__c', 'NetworkId__c', 'BasisOfPractice__c' }
                );

        // A13.10 — detect unused (existing rows that are no longer represented in the UI)
        List<HealthcareFacilityNetwork> toDeactivate = detectUnused(existing, shaped);

        Result r = new Result();
        r.toInsert     = toInsert;
        r.toDeactivate = toDeactivate;
        return r;
    }

    @TestVisible static List<NetworkRow> demergeByRole(List<NetworkRow> input) { ... }
    @TestVisible static List<NetworkRow> expandInfoCodes(List<NetworkRow> input,
                                                        List<InfoCodeDTO> codes) { ... }
    @TestVisible static List<HealthcareFacilityNetwork> shapeForInsert(List<NetworkRow> rows,
                                                                      PRM_HCFNetworkSelector.PayerData payer) { ... }
    @TestVisible static List<HealthcareFacilityNetwork> clonesForNewNetworks(...) { ... }
    @TestVisible static List<HealthcareFacilityNetwork> clonesForExistingNetworks(...) { ... }
    @TestVisible static List<HealthcareFacilityNetwork> detectUnused(...) { ... }
}
```

### 6.5 `PRM_OffCycleRerouteToQMService` (Branch B)

> **Why we need it** — When the committee can't decide ("Reroute to QM"), the flow needs to: (1) close the current PDA case with a structured note, (2) open a NEW QM case linked to the same IndividualApplication, (3) link the case manager, (4) record the reviewer's comment as a Note. Today this is 6 IP elements with 4 separate DR Posts; if step 2 fails after step 1 commits, the IndividualApplication has a closed PDA case with no follow-up — a known stuck state in production that requires manual intervention.
>
> **How it helps** — Single composing service that sequences the 4 steps with an explicit invariant: the new QM case is created BEFORE the PDA case is closed (not after). Reuses `PRM_CaseService.openCase` + `closeCase`, `PRM_OffCycleIdentifierService.attachUploadedDoc`, and `PRM_NoteService.create`. If the new QM case fails, the PDA case stays open — no orphaned IndividualApplication.
>
> **Outcome** — Stuck-state cases eliminated by reordering the invariant. Branch is testable with one fixture per failure mode.

```apex
public with sharing class PRM_OffCycleRerouteToQMService {
    public void reroute(OffCyclePDADTO dto, OffCyclePDAResult res) {
        res.newCaseId = PRM_CaseService.createCase(CaseFactory.forOffCycleRerouteQM(dto));
        PRM_CaseService.closeAndLinkNext(dto.oldCase(), res.newCaseId, dto.caseManager());

        if (dto.hasUploadedDoc()) {
            new PRM_OffCycleIdentifierService().attachUploadedDoc(dto, res.newCaseId);
        }
        if (dto.hasPdaNote()) {
            PRM_NoteService.createCaseNote(res.newCaseId, dto.pdaNote());
        }
    }
}
```

### 6.6 `PRM_OffCyclePDAAsyncJob` (Queueable for TX2)

> **Why we need it** — The NetworkQC heavy branch can hit 150-300 HCFN rows + Location/Address/Group inserts + taxonomies + NPI history + attestation stamps in a single approval. Today this all runs in the committee reviewer's submit transaction; Production has seen "Apex CPU time limit exceeded" with no breadcrumb beyond the user's spinner timing out. The heaviest committee approval in the past quarter took 6.2 s of sync CPU.
>
> **How it helps** — A Queueable that re-instantiates `PRM_OffCycleNetMgmtQCService` and replays its heavy steps in a fresh governor context. Same code path runs sync OR async — only the wrapping context changes. The decision is centralized in `PRM_GovernorUtil.shouldDelegateAsync(estimatedRowCount)`. On completion, publishes `PRM_AsyncComplete__e` with the case id and result payload — the reviewer's bell receives the success/failure update without a polling round-trip.
>
> **Outcome** — Reviewer receives caseId + status in <700 ms regardless of approval volume. Heavy work commits in TX2 with a fresh 10s/150-row budget. The 6.2-second approval becomes 0.7 s of perceived wait + 4 s of background work.

```apex
public class PRM_OffCyclePDAAsyncJob implements Queueable, Database.AllowsCallouts {
    private final OffCyclePDADTO dto;
    private final OffCyclePDAResult res;

    public PRM_OffCyclePDAAsyncJob(OffCyclePDADTO dto, OffCyclePDAResult res) {
        this.dto = dto;
        this.res = res;
    }

    public void execute(QueueableContext ctx) {
        PRM_TransactionContext.start('OffCyclePDAReview-Async', dto.requestId());
        try {
            new PRM_OffCycleNetMgmtQCService().runHeavyDml(dto, res);
        } catch (Exception e) {
            PRM_ErrorLogger.logException(e, dto.context());
            res.errors.add(e.getMessage());
        } finally {
            EventBus.publish(new PRM_AsyncComplete__e(
                JobName__c   = 'OffCyclePDAReview',
                ContextId__c = res.newCaseId,
                Success__c   = res.errors.isEmpty(),
                Payload__c   = JSON.serialize(res.toMap())
            ));
        }
    }
}
```

---

## 7. Sequence Diagram (target state, NetworkQC outcome)

```
QM User      OS:QMReview      ServiceDispatcher    SendToPDASvc      DB         PDA User      OS:PDAReview     PDAReviewSvc      NetMgmtSvc       AsyncJob          DB         QC User      OS:QCReview     NetworkQCSvc      DB
   │              │                   │                  │            │            │              │                   │                │                │                │            │              │                  │             │
   │ Send to PDA  │                   │                  │            │            │              │                   │                │                │                │            │              │                  │             │
   │─────────────►│ invoke('OffCycleSendToPDA')          │            │            │              │                   │                │                │                │            │              │                  │             │
   │              │──────────────────►│ ─────────────►   │            │            │              │                   │                │                │                │            │              │                  │             │
   │              │                   │                  │ DML(2 rows)│            │              │                   │                │                │                │            │              │                  │             │
   │              │                   │                  │───────────►│            │              │                   │                │                │                │            │              │                  │             │
   │              │◄──────────────────│ ◄────────────    │            │            │              │                   │                │                │                │            │              │                  │             │
   │ ◄── done ────│                   │                  │            │            │              │                   │                │                │                │            │              │                  │             │
   │              │                   │                  │            │            │   Open PDA   │                   │                │                │                │            │              │                  │             │
   │              │                   │                  │            │            │─────────────►│ invoke('OffCyclePDAReview') / PDAOutCome=NetworkQC                                  │            │              │                  │             │
   │              │                   │                  │            │            │              │──────────────────►│ ─────────────► │                │                │            │              │                  │             │
   │              │                   │                  │            │            │              │                   │                │ TX1 sync DML   │                │            │              │                  │             │
   │              │                   │                  │            │            │              │                   │                │───────────────────────────────►│            │              │                  │             │
   │              │                   │                  │            │            │              │                   │                │ enqueue async  │                │            │              │                  │             │
   │              │                   │                  │            │            │              │ ◄─ caseId ────────│                │                │                │            │              │                  │             │
   │              │                   │                  │            │            │              │                   │                │                │ runHeavyDml    │            │              │                  │             │
   │              │                   │                  │            │            │              │                   │                │                │───────────────►│            │              │                  │             │
   │              │                   │                  │            │            │              │                   │                │                │ AsyncComplete  │            │              │                  │             │
   │              │                   │                  │            │            │              │                   │                │                │                │            │   Sign off   │                  │             │
   │              │                   │                  │            │            │              │                   │                │                │                │            │─────────────►│ invoke('OffCycleNetworkQC')   │             │
   │              │                   │                  │            │            │              │                   │                │                │                │            │              │─────────────────►│ ──────────► │
   │              │                   │                  │            │            │              │                   │                │                │                │            │              │                  │ DML(4 rows) │
   │              │                   │                  │            │            │              │                   │                │                │                │            │              │ ◄────────────────│ ──────────► │
```

---

## 8. Governor / Performance Comparison

| Limit | Today (worst-case NetworkQC outcome with State+Region+Multi-Network) | After refactor (TX1) | After refactor (TX2 Queueable) |
|---|---:|---:|---:|
| SOQL queries | ~24 | 6 | 8 |
| DML statements | ~18 | 4 | 8 |
| DML rows | 150–350 | 4–6 | 150–350 (partial-success, chunked) |
| CPU time (ms) | 3,500–6,000 | < 700 | budget renewed in async slot |
| Heap | 3–5 MB | < 800 KB | 3–5 MB (renewed) |
| Remote Action calls | 4 (in `RA_DemergedFacilityNetwork`, `RA_InfoCodes`, `RA_DemergedNewHCFN`, `RA_DemergedExistingHCFN`) | 0 (pure-Apex transformer) | 0 |

The biggest single win is **eliminating the 4 Remote Action round-trips** for the HCFN reshape — those are pure transformation logic that today take a full Apex execute() round-trip each. Moving them into `PRM_OffCyclePDAHFNTransformer` keeps everything in a single Apex call.

---

## 9. Migration Plan

### 9.1 Sequencing

This document is **last** in the migration order:

1. Par Form (creation) Apex services land
2. PDA Review (initial cred) Apex services land — provides `PRM_AccountUpdater`, `PRM_TaxonomyService`
3. Off Cycle **Submit** services land — provides `PRM_OffCycleAddressService`, `PRM_OffCycleNetworkService`, `PRM_OffCycleGroupService`, `PRM_OffCycleIdentifierService`, every selector + transformer
4. **Off Cycle PDA Review services** — only need to add the 5 new orchestrators + 2 extensions + 4 small helpers + 1 transformer
5. Side-by-side under flag `PRM_FeatureConfig.OffCyclePDA_UseApexService`
6. Retire **6 IPs + ~14 DataRaptor bundles + 4 Remote Action methods** after burn-in

### 9.2 Components to retire after migration

| Type | Names |
|---|---|
| **Integration Procedures (6)** | `PRM_OffCycleCaseCaseMgrUpdatesSendToPDAParent`, `PRM_OffCycleCaseCaseMgrUpdatesSendToPDA`, `PRM_OffCycleRecordUpdatesPDAReviewParent`, `PRM_OffCycleRecordUpdatesPDAReview`, `PRM_OffCycleRecordUpdatesQCReviewContainer`, `PRM_OffCycleRecordUpdatesQCReview` |
| **DataRaptors — Post (~9)** | `PRMUpdatePractitionerPDAReview`, `PRMUpdateTaxonomyPDAReview`, `PRMDRPGroupNPIHcPractiFacility` (PDA variant), `PRMDRPOffcyclePDAFacilityLocAddr`, `PRMDRPOffCycleUpdateNPIHistory`, `PRMUpdateCaseCaseMgrNetQC`, `PRMUpdateCaseCaseMgrPDAReview`, `PRMUpdateCaseCaseMgrOffCycleSendToPDA`, `PRMDRPHCFNetwork` (the PDA call site only — same bundle is used by Off Cycle Submit, so the bundle itself stays but the call sites are removed) |
| **DataRaptors — Extract (1)** | `PRMDREOffcycleNPIHistory` |
| **DataRaptors — Transform (1)** | `PRMDRTransformHFNPDA` |
| **DataRaptors — Turbo (1)** | `PRMGetHealthCarePayerNetwork` (call sites only — leave bundle if shared) |
| **DataRaptors — Update (3)** | `PRMUpdateAttestationDateOnPracLoc`, `PRMUpdateAttestationDateForSpecialityChange` |
| **Remote Action methods (4)** | `PRM_OmniUtils.cloneBasisMultipleRole` (PDA call site — kept for Off Cycle Submit), `PRM_OmniUtils.cloneHCFNRecords` (same), `PRM_OmniUtils.expandInfoCodes` (or whichever util `RA_InfoCodes` calls — verify at migration time), `PRM_OmniUtils.createNoteMulti` (Stage 1 + Stage 2 + Stage 3 call sites collapse into `PRM_NoteService`) |

### 9.3 Test Strategy

| Layer | Tests |
|---|---|
| `PRM_OffCyclePDAHFNTransformer` | exhaustive pure-function unit tests — feed (existing HCFN + UI selection) and assert (toInsert / toDeactivate) for each (PDAOutCome × ChangeRequested) combo |
| `PRM_OffCycleNetMgmtQCService` | mock all 9 sub-services, assert call order + DTO routing per ChangeRequested |
| `PRM_OffCyclePDAReviewService` | one test per `PDAOutCome` value (Approve / RerouteToQM / NetworkQC × 7 change types) |
| `PRM_OffCycleSendToPDAService` / `PRM_OffCycleNetworkQCService` | 1 integration test each (Case + IndividualApplication + Identifier + Note) |
| Async | `Test.startTest()/stopTest()` to drain `PRM_OffCyclePDAAsyncJob` — assert TX2 records + `PRM_AsyncComplete__e` |
| OmniScript | 1 OS-level test per outcome — assert no change in JSON contract |

### 9.4 Feature Flag Rollout

```
PRM_FeatureConfig__mdt.OffCyclePDA_UseApexService     (Boolean, default false)
PRM_FeatureConfig__mdt.OffCyclePDA_AsyncThresholdRows (Integer, default 50)
```

Each of the three services reads the flag at the top of `processSync()` and falls through to the legacy IP via `PRM_LegacyIPProxy` if the flag is off.

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| `PRM_OmniUtils.cloneBasisMultipleRole`, `cloneHCFNRecords`, and the info-code expansion are **shared** with the Off Cycle Submit flow (and the original PDA Review for Initial Cred). | Move them into `PRM_NetworkCloneUtil` (shared lib) when the **first** migration that needs them lands (Off Cycle Submit). This document then just consumes the same util. |
| The HCFN reshape (A13.x) is the most complex piece of logic in the entire Off Cycle stack. Misreading the merge / dedup semantics could create duplicate HCFN rows. | Build the transformer **test-first** with parity tests against captured production payloads (use real form submissions stored in the existing logs). Run dual-write under the flag for at least 2 sprints, comparing the row sets. |
| `PRMDRPHCFNetwork` is the **same DR bundle** used by Off Cycle Submit (`Pending=TRUE`) and Off Cycle PDA Review (`Pending=FALSE`). Replacing one call site at a time without retiring the bundle is fine, but tests must cover both call sites. | Keep the bundle until **both** the Submit and PDA Review migrations have finished. The DR call sites collapse independently because each is wrapped by its own Apex service. |
| `PDAOutCome == "Approve"` today does no IP work — it is handled by an OS Set Values + Remote Action. The new `PRM_OffCycleApproveService` must replicate the exact same status transitions. | Move the OS `PDAUpdateOutcome` / `PDAUpdateOutcomeR` logic into the service in the **same release** as the flag flip; otherwise the OS will still try to do the update and we'll have a double-write. |
| `LocationNPIHistory` close-prior + open-new must remain atomic per Location. | `PRM_LocationNPIHistoryService.closePriorAndOpenNew` performs both writes in a single `Database.upsert` with `allOrNone=false` and validates that each Location either has both rows or rolls both back at the service layer. |
| QC reviewer's case (Stage 3) sometimes opens **before** the PDA's async job finishes. | The `PRM_AsyncComplete__e` event drives a Platform Event-triggered Flow that flips the case status to "Ready for QC" — Stage 3 is gated by that status. |
| Stage 1 (Send to PDA) and Stage 3 (Network QC sign-off) share 3 of 4 elements (Case + CaseMgr + Note); a careless implementation could create two services with copy-paste. | Both services delegate to `PRM_CaseService.createCase()` + `closeAndLinkNext()` + `PRM_NoteService.createCaseNote()`. The two service classes are 30–40 lines each, parameterised by a `CaseFactory` method (`forOffCycleSendToPDA`, `forOffCycleQCClose`, `forOffCycleNetworkQC`, `forOffCycleRerouteQM`). |

---

## 11. Acceptance Criteria

1. All three IPs (`PRM_OffCycleRecordUpdatesPDAReview`, `PRM_OffCycleRecordUpdatesQCReview`, `PRM_OffCycleCaseCaseMgrUpdatesSendToPDA`) shrink to 3 elements each (SetValues → ServiceInvoker → Response).
2. For every `PDAOutCome × ChangeRequested` combination, the row sets produced by the legacy IP and the Apex service are **bit-identical** under dual-write.
3. The `NetworkQC` worst case (State + Region + 5 networks × 4 roles, 3 new addresses) returns from the **synchronous** request in **< 800 ms** Apex CPU.
4. Async TX2 completes in **< 60 seconds** for that worst case, with `PRM_AsyncComplete__e` fired.
5. Zero changes required to `PRM_OffCyclePDAReview_English`, `PRM_OffCycleQCReview_English`, or `PRM_OffCycleQMReview_English` step JSONs.
6. Coverage ≥ 90% on every NEW class and ≥ 80% on each EXTENDED service.
7. Feature flag (`OffCyclePDA_UseApexService = false`) cleanly reverts to legacy IP path.
8. Total new Apex LoC ≤ 1,200 across all 8 NEW classes (excluding tests).

---

## 12. Net new vs reused — one final view

| Category | Net new code in *this* migration |
|---|---|
| Selectors | **0** (all exist after Off Cycle Submit) |
| Transformers | **1** (`PRM_OffCyclePDAHFNTransformer`) |
| Orchestration services | **6** (PDAReviewService, NetMgmtQCService, RerouteToQMService, ApproveService, SendToPDAService, NetworkQCService) |
| Helpers | **3** (`PRM_LocationNPIHistoryService`, `PRM_AttestationDateUpdater`, `PRM_OffCyclePDAAsyncJob`) |
| Extensions | **2** (`PRM_OffCycleNetworkService.processCommitteeApprovedNetworks`, `PRM_TaxonomyService.committeeApprove`) |
| **Approximate LoC** | ~1,100 (incl. DTOs), test code another ~1,400 |

Everything else — Case management, identifiers, notes, address transforms, group affiliation, account updates, NPI history selector, etc. — is **already on the shelf** after the previous three migrations.

---

## 13. Cross-references

- Generic framework: [`PNM_Apex_Service_Architecture.md`](./PNM_Apex_Service_Architecture.md)
- Par Form (creation): [`PNM_ParForm_RecordCreation_Apex_Service_Architecture.md`](./PNM_ParForm_RecordCreation_Apex_Service_Architecture.md)
- PDA Review (initial cred): [`PNM_PDA_ReviewUpdate_Apex_Service_Architecture.md`](./PNM_PDA_ReviewUpdate_Apex_Service_Architecture.md)
- Off Cycle Submit: [`PNM_OffCycle_Process_Apex_Service_Architecture.md`](./PNM_OffCycle_Process_Apex_Service_Architecture.md)







