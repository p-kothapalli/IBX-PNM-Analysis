# Group-Wide "Soft Termination" and Reinstatement — Solution Analysis

**Date:** 2026-08-19
**Status:** Analysis only. No user stories, no acceptance criteria, no code or metadata changed.
**Source prompt:** `requirements/SoftTerm_GroupWide_Reinstate_Analysis_Prompt.md`
**Grounding note:** the `code-review-graph` knowledge graph for this workspace contains **2 JavaScript nodes and 0 edges** (verified via `list_graph_stats_tool`), so it covers none of the Apex/OmniStudio surface. Per the fallback clause in `.cursor/rules/code-review-graph-first.mdc`, all grounding below was done with ripgrep/Glob/Read against `force-app/main/default/` and `requirements/`. Every component name is either marked **verified** (found on disk, path given) or **UNVERIFIED**.

---

## 1. Executive summary

**Recommendation in one paragraph.** Implement the soft term as a **network-scope termination only** — end the `HealthcareFacilityNetwork` (HFN) rows that carry the group's network participation, and leave the practitioner's `Account`, their `HealthcarePractitionerFacility` (HCPF) affiliation to the group, `Account.PRM_CredentialingStatus__c`, and `Account.PRM_ReCredDueDate__c` **untouched**. This is the only candidate that satisfies business's stated requirement — "credentialing lifecycle events that would have occurred anyway must still be honored" — *by construction* rather than by building a snapshot-and-restore engine. The reason is a hard, grounded fact: **every termination path that touches a practitioner Account nulls `PRM_ReCredDueDate__c`, on both the Full-Term branch and the Non-Par branch, and no reinstate component anywhere in this repo ever writes that field back.** Network-only termination never enters that code path, so the recredentialing clock keeps ticking, the recred/CAQH/PSV batches keep selecting the practitioner (they filter on `Account.IsActive = true`, which stays true), and reinstatement becomes a narrow HFN reactivation for which an Apex precedent already exists in both directions (`PRM_RCATNetworkTerminationBatch` terminates HFN-only; `PRM_UpdateHCFNForReInstate` reinstates HFN-only). The recommendation is **conditional on one unverified fact** — see Risk R1 and Open Question Q1.

### Top 5 risks

| # | Risk | Why it is the top of the list |
|---|---|---|
| **R1** | **The provider directory and member search may key off `Account.IsActive`, not network participation.** `PNM_Reinstate_Apex_Service_Architecture.md` §3.2 states "the directory and member-search expose `Account.IsActive`". If that is literally true, network-only termination will **not** take these practitioners out of the published directory, and business's core requirement is unmet by the recommended construct. | This single fact decides the whole solution. It is a downstream/out-of-Salesforce dependency and is **UNVERIFIED** in this repo. |
| **R2** | **Full termination irrecoverably destroys the recredentialing clock.** `PRM_PractitionerTerminationBatchHelper.setTermDataPractitioner` sets `PRM_ReCredDueDate__c = null` in **all three overloads**, unconditionally, on **both** the Full and Non-Par branches. No reinstate DataMapper, Apex class, or IP writes it back (verified by exhaustive grep). | If business proceeds with real termination, "honor the recred that would have happened" is impossible without a purpose-built snapshot. This is the single most likely business surprise. |
| **R3** | **Reinstatement stamps `PRM_CredentialingStatus__c = 'Credentialed'` as a hardcoded literal.** `PRMLoadOffCycleCaseCaseMgrReinstate_1` carries `<defaultValue>Credentialed</defaultValue>`. A practitioner whose recred lapsed during the window would be reinstated as *Credentialed* with **no due date** — a false credentialing attestation, and an audit finding waiting to happen. | Compliance exposure, not just data quality. |
| **R4** | **RCAT can terminate the cohort for real, mid-window.** A soft-termed practitioner who becomes recred-non-compliant during the two months flows into RCAT (`PRM_ReviewRCAT_English`, `PRM_RCATProcessingService`) and can be genuinely terminated, with a `PRM_Letter__c` RT `PRM_Termination` mailed to them — during an active negotiation. | Turns a reversible posture into an irreversible one, silently. |
| **R5** | **Neither the reinstatement mechanism business named nor the async framework it would ride on exists.** The delegated roster operation catalog has **no REINSTATE operation** (verified against `PRM_DelegatedRoster_CommonSchema.md` v1.1 and `PRM_StandardDelegatedRosterImportTemplate.md`), the roster upload LWC/Apex are *proposed, not built*, and `PRM_AsyncJob__c` / `PRM_AsyncJobDetails__c` / `PRM_AsyncJobRecords__c` **do not exist** under `objects/`. | The stated September delivery depends on three unbuilt layers. |

### Business decisions still required

**11** — enumerated in §11. Three are gating (Q1 directory read, Q2 gap vs retroactive continuity, Q3 termination-letter suppression) and must be answered before design starts.

---

## 2. Current-state findings

### 2.1 Verified — the two "soft vs hard" constructs that actually exist in Apex

There is no `SoftTerm`, `Suspend`, or `Hold` construct in this codebase. Searched: Apex class filenames matching `/SoftTerm|Suspend|Hold/i` (only false positives `PRM_ThresholdExceededException`, `DFX_ThresholdExceededException`), and object field filenames matching `Suspend` (only `CareProviderAdverseAction.PRM_SuspendedSentenceLength__c`, `MessagingSession.SuspendedByType`). What exists is a **Non-Par vs Full-Term** split, plus a **network-only** termination used by RCAT.

**The practitioner Account write path** — `force-app/main/default/classes/PRM_PractitionerTerminationBatchHelper.cls`, lines 714–772, three overloads:

```
setTermDataPractitioner(practitioner, isFull, termDate, termReason, caseManagerId [, parentEffectiveTo | pdm])
    PRM_CredentialingStatus__c = 'Terminated'      // unconditional in overload 1; date-guarded in 2 and 3
    PRM_ReCredDueDate__c       = null              // ALL THREE OVERLOADS, UNCONDITIONAL, BOTH BRANCHES
    PRM_TerminationReason__c   = termReason
    PRM_CaseManager__c         = caseManagerId
    if (isFull)  { PRM_EffectiveTo__c = min(existing, termDate); IsActive = termDate > TODAY;
                   PRM_NonParticipatingStartDate__c = null }
    else         { PRM_ParticipationStatus__c = 'Non-Par';
                   PRM_NonParticipatingStartDate__c = termDate }
```

Two conclusions follow, and they are the backbone of this analysis:

1. **Non-Par is not a credential-preserving state at the practitioner level.** It stamps `PRM_CredentialingStatus__c = 'Terminated'` (overload 1) and nulls the recred due date exactly like Full-Term. Non-Par only differs in that it leaves `PRM_EffectiveTo__c` and `IsActive` alone and instead sets `PRM_ParticipationStatus__c = 'Non-Par'` + `PRM_NonParticipatingStartDate__c`. **ASSUMPTION:** the intent of Non-Par was "still in our data, no longer in our networks" — but the implementation also declares them un-credentialed.
2. **Nothing restores the recred clock.** `rg -il "PRM_ReCredDueDate__c"` across `classes/` and `omniDataTransforms/` returns 49 files; **not one** has `Reinstate` in its name. The writers are the PSV batch helper, `PRM_PARReCredCommitteeReviewBatch` (approve → +3 years), `PRM_RecalculatePNCFlowAction`, `PRM_PDMDataHelper`, `PRM_UpdateCaseManagerBatch`, `PRM_CommitteeReviewHelper`, `PRM_RCATProcessingService`, and the termination helpers (which null it).

**Callers of the Non-Par branch** (`isFull = false`) — verified: `PRM_PracticeLocationTerminationBatch` (line 372), `PRM_ManualUpdatePracLocTerminationBatch` (line 112), `PRM_AccountTerminationBatchHelper.transformNonParPractData` (line 479), `PRM_CrossRefBatchHelper` (line 304), `PRM_ManualUpdatesCrossRefBatchHelper` (line 490), `PRM_PDMUnlinkPractitioner` (line 234), `PRM_FullPractitionerTerminationBatch` (line 203).

**Non-Par at the location level** is a separate, genuinely lighter construct: `HealthcareFacility.PRM_NonParLocation__c` + `HealthcareFacility.PRM_NonParticipatingStartDate__c` (both verified). Per `requirements/RCAT_PracticeLocation_NonPar_FullTerm_Batch_UserStory.md`, wiring these from the RCAT/Recred-Updates path is **proposed, not built** — today only the practitioner/account Non-Par fields are set from that lane.

### 2.2 Verified — the termination reason taxonomy already routes a negotiation posture to Non-Par

`force-app/main/default/objects/Account/fields/PRM_TerminationReason__c.field-meta.xml` — 16 values: `Deceased`, `Retired`, `Filing Under Another TIN/NPI`, `Voluntary Withdrawal`, `Out of Business`, `Merger`, `Duplicate Provider Number`, `Change of Ownership`, `Administrative Decision - for Cause`, `Administrative Decision - Not for Cause`, `Unknown`, `Failure to Re-Credential`, `CMS Preclusion`, `CMS Sanction`, `NPI Deactivation`, `PHO Termination`.

`PRM_GlobalConstant.FULLTERMREASON` (line 387) = `{'Deceased', 'Retired', 'Administrative Decision - for Cause', 'CMS Preclusion'}`. Any other reason routes to **Non-Par**.

A contract renegotiation is `Administrative Decision - Not for Cause` (or arguably `PHO Termination`), neither of which is in `FULLTERMREASON` — so **if business uses the existing Account/Vendor Termination flow with an honest reason code, the system already produces a Non-Par, not a Full Term.** There is **no** `Contract Negotiation` value. `PRM_ParticipationStatus__c` values are `Participating` / `Non-Par` / `Administrative` / `Terminated`.

### 2.3 Verified — the network layer, and what "network termination" means here

`PractitionerLocationNetwork` and `PractitionerNetwork` **do not exist** as objects in this repo (searched `force-app/main/default/objects/`). This confirms `CLAUDE.md` CL-3 and means the three-object model described in `requirements/MassNetworkAddTerminate_TaxIdNpi_UserStories.md` is **partly aspirational**. All network participation is carried on **`HealthcareFacilityNetwork`**, differentiated by record type:

| HFN record type (verified on disk) | Carries |
|---|---|
| `PRM_FacilityNw` | Facility ↔ network participation |
| `PRM_FacilityTx` | Facility ↔ taxonomy |
| `PRM_FacilityPractitionerTxNw` | **Practitioner × taxonomy × network at a facility** — the practitioner-level network row |
| `PRM_TaxonomyNetworkException` | Taxonomy/network exception |

Relevant HFN fields (verified in `objects/HealthcareFacilityNetwork/fields/`): `HealthcareFacilityId`, `PractitionerId`, `PractitionerFacilityId`, `PayerNetworkId`, `ProviderNetworkContractId`, `ProviderNetworkTierId`, `EffectiveFrom`, `EffectiveTo`, `IsActive`, `PanelStatus`, `PRM_TerminationReason__c`, `PRM_ChangeReason__c`, `PRM_CaseManager__c`, `PRM_IsErrorRecord__c`, `PRM_FacilityNetworkEffectiveToday__c`, `PRM_NetworkParticipationType__c`, `PRM_PractitionerRole__c`, `PRM_Taxonomy__c` / `PRM_TaxonomyCode__c`, and the `PRM_RoleEffectiveFrom__c` / `PRM_TaxonomyEffective*` / `PRM_PanelStatusEff*` date sets.

**Existing network-only termination in Apex:** `PRM_RCATNetworkTerminationBatch` — writes **only** `HealthcareFacilityNetwork` (`EffectiveTo`, `IsActive`, `PRM_IsErrorRecord__c`, `PRM_CaseManager__c`) via `PRM_RCATTerminationBatchHelper.resolveEffectivity`. Its selection is `WHERE PractitionerId IN :conIds AND HealthcareFacilityId IN :hfIds AND RecordTypeId = :hcfNxTx AND PRM_IsErrorRecord__c = false`.

**Existing network-only reinstatement in Apex:** `PRM_UpdateHCFNForReInstate` — batch that updates `HealthcareFacilityNetwork` (`IsActive`, `EffectiveFrom`, `EffectiveTo`, `PRM_CaseManager__c`) and routes failures to `PRM_FailedRecordStaging__c`. Its test asserts the practitioner Account ends at `PRM_ParticipationStatus__c = 'Participating'`.

**`resolveEffectivity`** — `PRM_RCATTerminationBatchHelper.resolveEffectivity` (~lines 399–425), verified. Rule (per `RCAT_PracticeLocation_NonPar_FullTerm_Batch_UserStory.md` AC-6): if `EffectiveFrom >= terminationDate` → error record (`EffectiveFrom = TODAY`, `PRM_IsErrorRecord__c = true`, active false, `EffectiveTo` null); else `EffectiveTo` = blank→termDate, earlier→unchanged, later→termDate; `IsActive = (EffectiveFrom <= TODAY && EffectiveTo > TODAY)`; stamp `PRM_CaseManager__c`. **Any soft-term implementation must reuse this, not re-derive it.**

### 2.4 Verified — the four roster termination scopes exist only on paper

| Literal | In `force-app/`? | In `requirements/`? |
|---|---|---|
| `TERM_NETWORK`, `TERM_GROUP`, `TERM_CONTRACT`, `TERM_AFFILIATION` | **No** | Yes — `PRM_DelegatedRoster_CommonSchema.md`, `PRM_StandardDelegatedRosterImportTemplate.md` |
| `endNetworkMembershipsOnly` | **No** | Yes — same docs |
| `lastManStanding` | **Yes** — `PRM_OmniProcessUtils` / `PRM_OmniProcessUtilsHelper.lastManStandingValidation`, IP `PRM_ValidateLastManStandingPractitioner_Procedure_1`, `PRM_PractitionerDataForVendorTermHelper`, `PRM_FutureDatedProcessingUtil`, `PRM_ActiveLocationsControllerHelper` | Yes |
| `resolveEffectivity` | **Yes** — `PRM_RCATTerminationBatchHelper` | Yes |
| `NonPar` / `nonParticipating` | **Yes** — widespread (fields, DRs, OmniScripts, Apex) | Yes |

### 2.5 Verified — active OmniStudio versions for the term/reinstate surface

Only the version with `<isActive>true</isActive>` is live. Inspected versions:

| Asset | Active version |
|---|---|
| OmniScript `PRM` / `PractitionerReinstateForm` / `English` | **v9** |
| OmniScript `PRM` / `PracticeLocationReinstate` / `English` | **v6** |
| OmniScript `PRM` / `PractitionerReinstateVendorForm` / `English` | **v5** |
| OmniScript `PRM` / `ReinstateLinkExistingPractitioner` / `English` | **v1** (only version) |
| OmniScript `PRM` / `AccountTerminationForm` / `English` | **v9** |
| OmniScript `PRM` / `PracticeLocationTermination` / `English` | **v18** |
| OmniScript `PRM` / `PractitionerTerminationForm` / `English` | **v31** |
| OmniScript `PRM` / `PractitionerTerminationRecredForm` / `English` | **v4** |
| IP `ReinstateRecordCreation` | **v4** (`PRM_ReinstateRecordCreation_Procedure_4`) |
| IP `ReinstatePracticeLocation` | **v8** |
| IP `PractitionerReinstateVendorUpdate` | **v6** |
| IP `AccountTermination` | **v17** |
| IP `PracticeLocationTermination` | **v11** |
| IP `PractitionerTerminationRecordsRecredUpdate` | **v11** |
| IP `GetPractitionerTerminationData` | **v4** |

**Metadata anomalies worth flagging to the team (verified):** IP `PractitionerTerminationRecordsUpdate` has **both v25 and v26 with `isActive=true`**, and `FetchPractNPIForTermination` has **both v2 and v3 active**. Two active versions of the same IP subtype is a deployment hazard independent of this project.

All 21 Reinstate-named and 56 Termination-named DataMappers under `omniDataTransforms/` are v1.0 with `<active>false</active>` on disk — normal for DR packaging in this repo (they are invoked by name from IPs), not evidence that they are unused.

### 2.6 Verified — what reinstatement restores, and what it does not

Grounded from `PNM_Reinstate_Apex_Service_Architecture.md` plus direct inspection of the DataMappers.

| Restored | Mechanism |
|---|---|
| `Account.IsActive = TRUE`, `PRM_Active__c`, `EffectiveTo = NULL`, reinstate date | `PRMDRPractitionerAccountUpdate` |
| `Account.PRM_ParticipationStatus__c` | `PRMDRToUpdateRecordsAfterReInstate_1` — mapped from input `ParticipationCode` |
| `Account.PRM_CredentialingStatus__c = 'Credentialed'` | `PRMLoadOffCycleCaseCaseMgrReinstate_1` — **hardcoded `<defaultValue>Credentialed</defaultValue>`** |
| `Account.PRM_NonParticipatingStartDate__c = null` | `PRMLoadOffCycleCaseCaseMgrReinstate_1` — `<defaultValue>$vlocity.null</defaultValue>` |
| HCPF, HFN, `Identifier__c`, `BoardCertification`, `PRM_InfoCodeAssignment__c`, `HealthcareProviderTaxonomy`, `PRM_ProviderFeature__c`, `HealthcareFacility`, `Location`, `Address` | per-row reactivation DRs, gated by the user's `ReinstateAs` / `Update` choices |
| **NOT restored** | |
| **`Account.PRM_ReCredDueDate__c`** | **nothing writes it — verified by exhaustive grep** |
| Anything the user did not tick | `ReinstateAs = false` → `toLeaveAlone` bucket |

**`ReinstateAs` × `Update` semantics** (from the architecture doc, and the reason a file-driven reinstate is hard): the OmniScript collects two flags per sub-entity row and partitions into `toReinstateAndUpdate` (reinstate + update fields), `toReinstateButDontUpdate` (reactivate only), and `toLeaveAlone`. The doc records a **live bug** in the IP: a row with `reinstateAs=true AND update='Yes'` can land in **both** reinstate buckets, causing duplicate DML. Volume: a worst-case practitioner reinstate is **~150–300 UPDATE rows**, and the practitioner IP already burns **4–7.5 s CPU** and breaches with 25+ HCPFs.

**Vendor path:** `PRM_ReinstateVendorAccountBatch` + `...Helper` runs when `PracticeLocationCount > 10`, invoked from `PRM_ReinstateCallable` as `Database.executeBatch(batch, 5)` — **batch size 5**, `Database.Stateful`, ~600 LoC. ≤10 locations runs inline via DR Posts.

**The ghost-practitioner hazard** (§3.2 of the architecture doc): flipping `Account.IsActive = true` before child reactivations land exposes a practitioner in the directory whose HCPF/HFN/Identifier rows are still inactive. The doc's mitigation (`PRM_ReinstateStatus__c` = In-Flight, Account flip last and gated on an empty error list) is **proposed target architecture, not built** — today's practitioner reinstate runs fully synchronously.

### 2.7 Verified — the effective-date cascade any term/reinstate must keep aligned

From `FutureDated_Termination_PushOut_UnitTest_Scenarios.md` §2, the vendor-account termination cascade spans **16 object types**: `Account`, `HealthcareProvider`, `Identifier`, `HealthcareFacility`, `Schema.Location`, `Schema.Address`, `HealthcareFacilityNetwork` (RTs `PRM_FacilityNw` / `PRM_FacilityTx` / `PRM_FacilityPractitionerTxNw`), `PRM_HealthcareFacilityAssociation__c`, `PRM_HealthcareFacilityBundleAssociation__c`, `PRM_InfoCodeAssignment__c`, `PRM_ProgramParticipation__c`, `HealthcarePractitionerFacility`, `HealthcareProviderNpi`, `HealthcareProviderTaxonomy`, `PRM_ContactMethod__c`, `PRM_FutureDatedProcessing__c`. The practitioner cascade adds `BoardCertification` and HCPF RTs `PRM_PractitionerLocationAffiliation` / `PRM_AdmittingPrivileges`.

`PRM_FutureDatedProcessing__c` (verified to exist) stages one open `Activate` and one open `Terminate` row per record, keyed by `PRM_ExternalId__c` = `{recordId}_Activate|_Terminate`, applied by `PRM_FutureDatedProcessingBatch` where `PRM_Processed__c = FALSE AND PRM_EffectiveDate__c = TODAY` and status matches — driven by `PRM_FutureDatedProcBatchSchTermination` / `...Activation` (all verified to exist). A third status, `Terminate - Last Man Standing`, is set by `PRM_FutureDatedProcessingUtil`.

### 2.8 UNVERIFIED / not present — things named in requirements that are not in this repo

Each of these is cited as existing somewhere in `requirements/` but is **absent from `force-app/main/default/`**. Any plan that depends on them needs a build, not a reuse.

| Named component | Searched for | Result |
|---|---|---|
| `PRM_sendGridNotifications` | exact class name, `*sendgrid*` case-insensitive | **NOT FOUND.** Closest: `PRM_SendGridEmailProcessor`, constant `PRM_GlobalConstant.SENDGRID_RECRED_TEMPLATE = 'SendGridRecredTemplate'` |
| `PRM_SendGridRecredTemplateIBC` / `..._AH` | exact names | **NOT FOUND** as classes |
| `PRM_ReCredToInitialCredConversion__c` | `objects/**/fields/`, all classes | **NOT FOUND.** Only `omniDataTransforms/PRMTRecredToInitialCredConversionProcess_1.rpt-meta.xml` exists. The field is **planned, not deployed** |
| `PRM_AsyncJob__c`, `PRM_AsyncJobDetails__c`, `PRM_AsyncJobRecords__c` | `objects/` | **NOT FOUND** — the high-volume async framework (`CLAUDE.md` Epic A) is not built |
| `PRM_AsyncJobRequest__c`, `PRM_AsyncJobQueued__e`, `PRM_SubmitAsyncJob`, `PRM_AsyncJobDispatcher` | objects, classes, events | **NOT FOUND** |
| `PRM_MassAddNetworkBatch`, `PRM_MassRemoveNetworkBatch`, `prmMassUpdateHub` | classes matching `/mass/i`, all LWCs | **NOT FOUND** — no Apex class or LWC matches. `MassNetworkAddTerminate_TaxIdNpi_UserStories.md` describes these as existing "Wave 4"; they are not in this metadata tree |
| `prmRosterUpload`, `prmRosterGrid`, `PRM_RosterEnvelopeBuilder`, `PRM_RosterValidator`, `PRM_RosterSubmitController`, `PRM_RosterCreationQueueable` | LWCs, classes | **NOT FOUND** — the file-upload design plan is a design, and says so |
| `PRM_ReinstatePractitionerService` and the proposed reinstate Apex SOA | classes | **NOT FOUND** — proposed in the architecture doc |
| `PRM_RecredDuePractitionersReportBatch` | classes | **NOT FOUND** (cited in a SOQL archive note) |
| `PRM_ReinstateStatus__c` | `objects/IndividualApplication/fields/` | **NOT FOUND** — proposed |

**What *does* exist for async/bulk:** `PRM_AsyncProcess__c` (7 custom fields only: `PRM_Type__c`, `PRM_SubType__c`, `PRM_Status__c`, `PRM_StartTime__c`, `PRM_EndTime__c`, `PRM_ItemsProcessed__c`, `PRM_ItemsFailed__c`), `PRM_FailedRecordStaging__c`, `PRM_ExceptionLog__c` + `PRM_ExceptionLogEvent__e`, `PRM_ExceptionLogger`, `NetworkMember`, `NetworkMemberChunk`, `PRM_UPHSRosterRecordsSyncBatch`, `PRM_UPennRosterRecordsSyncBatch`, and `PRM_ReinstateVendorAccountBatch`.

---

## 3. Soft-term construct options

### 3.1 Comparison

Scored against the two things business actually asked for: **(a) they are out of network for ~2 months**, and **(b) credentialing lifecycle events are honored, so they return with continuous history**.

| # | Candidate | Objects touched | Preserves recred clock? | Reversible? | Reuse available | Verdict |
|---|---|---|---|---|---|---|
| **A** | **Network-scope termination only** — end HFN rows (`PRM_FacilityNw`, `PRM_FacilityTx`, `PRM_FacilityPractitionerTxNw`), keep HCPF / Account / cred status | 1 object, 1–3 record types | **Yes** — never enters `setTermDataPractitioner` | **Yes** — `PRM_UpdateHCFNForReInstate` already does exactly this | `PRM_RCATNetworkTerminationBatch` (term), `PRM_UpdateHCFNForReInstate` (reinstate), `resolveEffectivity` | **RECOMMENDED**, conditional on Q1 |
| **B** | **Non-Par conversion** (existing RCAT/Account-Termination Non-Par path) | Account + facility + the info-code / program-participation / contract-entity children | **No** — nulls `PRM_ReCredDueDate__c` and stamps `PRM_CredentialingStatus__c = 'Terminated'` | Partially — reinstate sets `Participating` + `Credentialed`, but not the due date | Substantial (`PRM_AccountTerminationBatchHelper.transformNonParPractData`) | **Rejected as primary.** It is the closest thing to a pre-existing soft term and it is what the reason taxonomy would pick by default — but it fails requirement (b) |
| **C** | **Full termination + later reinstate** (the three guided reinstate flows) | 16-object cascade | **No** — same nulling, plus `IsActive = false` | Partially, at high cost — 150–300 UPDATEs/practitioner, 4–7.5 s CPU, no roster reinstate op, known duplicate-bucket bug, ghost-practitioner hazard | The three reinstate flows exist but are per-practitioner and human-driven | **Rejected.** Maximum data damage, minimum fidelity |
| **D** | **Future-dated termination with push-out** | Live records + `PRM_FutureDatedProcessing__c` | Yes *while pending* (nothing has fired) | Cancel is **explicitly not built** (`FutureDated_Termination_PushOut_AddressUpdate_UserStory.md` §6) | `PRM_FutureDatedProcessingBatch` + schedulers | **Rejected as the primary construct, recommended as a complement.** It does not make them out-of-network during the window — they stay participating until the date lands. And push-out is a **known live defect**: re-terminating with a later date often changes no field, so no trigger fires, the FDP row keeps the **stale earlier date**, and the termination executes early while the UI reports success |
| **E** | **New suspension / hold flag** | 1 new field + every reader | Yes, by design | Yes, by design | **None** — no suspend/hold construct exists | **Rejected.** Nothing reads it. Every batch, directory feed, claims interface, and report would need to learn about it. Violates "prefer citing an existing mechanism"; A gets the same outcome using rows that consumers already read |

### 3.2 Recommendation and rationale

**Adopt Candidate A — network-scope termination only — for the practitioner cohort, and use Candidate D (future-dated termination on the vendor contract) as the negotiation-leverage instrument if business needs a formal notice on the record.**

Why A wins, in order of weight:

1. **It makes requirement (b) free.** Every other candidate requires reconstructing state that termination destroyed. A never destroys it. The recred/CAQH/PSV batches select on `Account.IsActive = true` and `PRM_ReCredDueDate__c`; both are untouched, so recredentialing during the window simply *happens*, correctly, and there is nothing to remediate at reinstatement. This collapses §5.3 (state capture) and most of §5.4 (missed processes) from "build a snapshot engine" to "verify no-op".
2. **Both directions already exist in Apex, at the same layer.** `PRM_RCATNetworkTerminationBatch` writes only HFN; `PRM_UpdateHCFNForReInstate` reactivates only HFN and already routes failures to `PRM_FailedRecordStaging__c`. The delta is cohort selection and a reason marker, not a new engine.
3. **It is the smallest blast radius on the 16-object cascade.** One object, and the FDP staging rows for that object only.
4. **It matches the roster schema's own intent.** `termination.scope = NETWORK` + `endNetworkMembershipsOnly = true` is exactly this shape, so a future roster implementation lines up rather than diverging (§7).
5. **It avoids the ghost-practitioner hazard entirely** — `Account.IsActive` is never flipped, so there is no window where the Account and its children disagree.

**Which of the four roster scopes matches business intent:** **`NETWORK`**, with `endNetworkMembershipsOnly = true`. Not `AFFILIATION` (would end HCPF and trigger last-man-standing), not `GROUP` (explicitly triggers last-man-standing on the whole TIN), not `CONTRACT` unless business is terminating a specific PO rather than network participation — worth confirming (Q4).

**Will `lastManStanding` fire?** Under A, **no** — last-man-standing is driven by ending the *affiliation* (`HealthcarePractitionerFacility`), and A does not touch HCPF. `PRM_FutureDatedProcessingUtil` computes its LMS map from affiliation counts, and `PRM_OmniProcessUtilsHelper.lastManStandingValidation` guards the affiliation-removal path. This is a decisive advantage: under Candidates B or C, terminating every practitioner under the group **would** trip last-man-standing and cascade the practice locations and the group itself out from under the cohort — turning a two-month pause into a structural teardown. **Any implementation of A must include an explicit regression test asserting LMS does not fire.**

**The condition.** A is correct *if* the consumers that must stop seeing these practitioners read network participation. If the provider directory reads `Account.IsActive` (as `PNM_Reinstate_Apex_Service_Architecture.md` §3.2 asserts), A leaves them published and business's commercial goal is unmet. That is **Q1**, and it gates everything.

**Fallback if Q1 goes badly:** A + a directory-suppression marker on the practitioner Account that is *not* `IsActive` and *not* a credentialing field — the same shape as the proposed `PRM_ReinstateStatus__c` In-Flight flag. That is a new field (Candidate E's weakness) but scoped to one consumer instead of all of them.

---

## 4. Cohort definition

### 4.1 Resolution rule

**Grounded, not proposed.** A vendor group is an `Account` with record type **`PRM_Vendor`** (there is no `PRM_VendorAccount` object). Tax ID is **`Account.HealthCloudGA__TaxId__c`**. "All practitioners under the group" resolves through **`HealthcarePractitionerFacility`** where `AccountId = <vendor Account Id>` and `RecordType.DeveloperName = 'PRM_PractitionerPracticeAffiliation'` and `IsActive = true`. This is the pattern already implemented in `PRM_PractitionerDataForVendorTermHelper.getPractitionerFromHcpFacility` and `PRM_PractitionerTerminationBatchHelper.getVendorPracticeToPractitioner` — **reuse these, do not write a new resolver.**

Group NPI is **not** a single Account field. It resolves via `HealthcareFacility.PRM_NpiId__c` → `HealthcareProviderNpi`. UI wrappers use the keys `GroupNPI` / `ExistingGroupNPI`. `MassNetworkAddTerminate_TaxIdNpi_UserStories.md` Clarification #6 leaves "is Group NPI the group Account NPI or the facility NPI?" **open** — inherit that open item, do not silently pick one (Q5).

Recommended selection: **Tax ID + vendor Account Id**, with Group NPI as a confirmation display rather than a join key, because Tax ID + Account Id is unambiguous in the data model as it exists. Full SOQL is archived at `requirements/SOQL/2026-08-19_SoftTermGroupWideCohort.md`.

### 4.2 Inclusion / exclusion edge cases

| Case | Treatment under Candidate A | Confidence |
|---|---|---|
| **Practitioner affiliated to this group *and* others** | Safe by construction. A terminates HFN rows filtered by `HealthcareFacilityId IN <this group's facilities>`, so other groups' HFN rows are untouched. Under B or C this is the highest-risk case — those paths write the shared practitioner `Account`, which is global. **This alone is a strong argument for A.** | Verified |
| **Practitioner whose only affiliation is this group** | Under A, no different from any other — HCPF survives, LMS does not fire. Under B/C this is the last-man-standing cascade. | Verified |
| **Mid-flight practitioners** (PSV, QC, committee, PDA, RCAT, off-cycle) | **Business decision (Q6).** Recommended default: **include** them in the network term (they are commercially out) but **do not touch their Case Manager or stage** — the in-flight work continues and completes normally, which is precisely business's stated intent. Exception: anything already in **RCAT** must be excluded and frozen (R4). | Recommendation |
| **Practitioners added to the group during the window** | Delegated roster adds keep arriving. Recommended default: new adds land **participating** (normal creation), and a **standing exclusion** keeps them out of the reinstatement file so they are not double-processed. Requires the cohort marker (§8) to be stamped at term time, not re-derived at reinstate time. | Recommendation |
| **Practitioners who genuinely leave during the window** | Must not be reinstated. Detectable because a real departure ends the **HCPF affiliation**, which the soft term did not touch. Reinstatement must therefore be gated on `HealthcarePractitionerFacility.IsActive = true` at reinstate time — a natural, grounded guard that Candidate C cannot offer (under C the affiliation is already ended, so real and soft departures are indistinguishable). | Verified reasoning |
| **Practice locations, addresses, NPIs** | **Out of scope** under A. Facility-level network participation (`PRM_FacilityNw`, `PRM_FacilityTx`) is in scope only if business intends the *locations* to be out of network too (Q7). | Business decision |
| **Info codes, program participation, provider features, taxonomy, board certs, identifiers, contact methods** | **Out of scope** under A — untouched, which is the point. All are in scope under B/C. | Verified |
| **Ancillary / facility / organizational providers under the same TIN** | **Business decision (Q8).** Different lifecycle (`PRM_AncillaryAssessment__c`, `PRM_CheckDueOnAncillaryReAssessmentBatch` filters on vendor `Account.IsActive = true`). Recommended default: **exclude** from the pilot cohort and handle as a separate decision. | Recommendation |

---

## 5. State capture and effective-dating model

### 5.1 Is a pre-termination snapshot required?

**Under Candidate A: no — and this is the single largest cost avoided.** The state that a snapshot would have to capture (cred status, recred due date, affiliations, taxonomies, identifiers, board certs) is never mutated, so there is nothing to restore. The only thing that must be recoverable is *which HFN rows were closed by this action*, and that is recoverable from the rows themselves (§8).

**Under B or C: yes, and it must be purpose-built.** Reconstruction from existing sources does not work:

- **Field history** — `PRM_ReCredToInitialCredConversion__c` shows the pattern of enabling history tracking, but Account field history is retained on a rolling window and is not queryable in bulk from Apex in a supported way for 200+ practitioners. Not a reliable system of record.
- **`PRM_CaseDataManager__c`** — exists, and reinstate stamps flags on it, but it records *which object families were touched by a Case Manager*, not prior field values.
- **`PRM_FutureDatedProcessing__c`** — holds a target date and record Id, not a value snapshot.
- **The termination Case Manager (`IndividualApplication`)** — records the reason, date, and type (`PRM_TerminationReason__c`, `PRM_TerminationType__c`) but not the practitioner's prior recred due date.

So under B/C a new staging object would be required — which is exactly the kind of net-new construct the constraints ask us to justify against reuse. We cannot justify it, which is another reason to prefer A.

### 5.2 Who supplies `ReinstateAs` / `Update` when the input is a file?

The guided flows collect two flags per sub-entity row from a human. A file cannot. Four options, evaluated:

| Option | Assessment |
|---|---|
| Default-all-yes | Dangerous under C — reinstates rows a human would have left alone, and walks straight into the known duplicate-bucket bug (`reinstateAs=true` + `update='Yes'` landing in both buckets). |
| Derive from the term snapshot | Correct in principle, requires the snapshot from §5.1 to exist. |
| Template column per sub-entity | Unworkable — the practitioner reinstate has 10 sub-entity families; the template already has 15 control + 91 data columns. |
| Analyst triage screen before submit | Best of the four for C, but reintroduces per-practitioner human decisions at cohort scale — the thing bulk was supposed to eliminate. |
| **Not applicable under A** | **A has no per-row matrix.** There is exactly one decision per HFN row: reopen or new period (§5.4). This is the cleanest answer to §5.3 of the prompt. |

### 5.3 Effective-date arithmetic — gap vs retroactive continuity

Term Sep 1, reinstate Nov 1. The prompt is right that these are completely different animals, and the correct answer is **not the same at every layer**:

| Layer | Recommended | Why |
|---|---|---|
| **Network participation (HFN)** | **Gap.** `EffectiveTo = <term date>`, participation resumes `EffectiveFrom = <reinstate date>`. | Claims incurred Sep–Nov must adjudicate out-of-network. Retroactive continuity would silently make two months of already-adjudicated claims wrong and invite re-adjudication and recovery exposure. |
| **Credentialing (HCPF affiliation, cred status, recred clock)** | **Continuity — unbroken, because never broken.** | This *is* business's requirement. Under A it is automatic. |

**That split is the core recommendation of this analysis**: a gap in network participation and unbroken continuity in credentialing, which is precisely what network-only scope produces and what no other candidate can produce without reconstruction. Gap vs retroactive is still formally a business/compliance answer for the network layer (**Q2**), but the recommended default is a gap, and choosing retroactive continuity should require explicit sign-off naming who owns the claims exposure.

### 5.4 Reopen the original row, or create a new period row?

| Approach | Consequence |
|---|---|
| **Reopen** (`EffectiveTo = null`, `IsActive = true` on the original HFN row) | What `PRM_UpdateHCFNForReInstate` does today. Cheapest. **But it erases the evidence that a gap existed** — after reinstatement the row looks like continuous participation, which contradicts the claims posture and defeats the audit requirement in §8. |
| **New period row** (close the original at `EffectiveTo = <term date>`, insert a new HFN row with `EffectiveFrom = <reinstate date>`) | Preserves an auditable gap. Matches the `LocationNPIHistory` "close prior before opening new" convention the architecture doc calls out. Costs one insert per row and needs the `PRM_FacilityPractitionerTxNw` taxonomy/role/panel date sets (`PRM_TaxonomyEffectiveFrom__c`, `PRM_RoleEffectiveFrom__c`, `PRM_PanelStatusEffFrom__c`) populated on the new row. |

**Recommendation: new period row**, with the caveat that this extends `PRM_UpdateHCFNForReInstate` rather than reusing it verbatim.

### 5.5 Effect on "oldest active PPL" / P2P derivation

Grounded from `P2P_EffectiveFrom_From_Oldest_Active_PPL_Impact_Analysis.md` and `P2P_EffectiveTo_Override_Scenarios.md`. P2P = `HealthcarePractitionerFacility` RT `PRM_PractitionerPracticeAffiliation`; PPL = RT `PRM_PractitionerLocationAffiliation`.

**Under Candidate A: no impact.** Neither RT is touched, so `MIN(EffectiveFrom)` over active PPLs and the `EffectiveTo` union rule are undisturbed. This matters because the corrective helper those docs propose — `PRM_HCPFTriggerHelper.syncP2PEffectiveFromOldestActivePPL`, behind `PRM_FeatureConfigurationSettings__c.PRM_EnableP2PEffectiveFromAutoSync__c` — is **not built and defaults off**. Any candidate that perturbs PPLs at cohort scale would be doing so on top of five documented open gaps (G1–G5), including "**no re-open on reinstate**": today reinstatement leaves a stale `EffectiveTo` on P2P. Candidates B and C would hit that at 200+ practitioner scale.

---

## 6. Process inventory for the two-month window

The most important deliverable. Read as: **does this fire today for a practitioner in the soft-term state, and is that correct?** "Network-only" is the recommended construct (Candidate A). "Full term" is shown for contrast because it is what business's plain-language request implies. Trigger criteria are verbatim-verified from each class's `start()` / query method unless marked otherwise.

Verdict key: **Allow** = fires, and that is correct · **Allow+Honor** = fires, correct, and its output must survive to reinstatement · **Suppress** = must be prevented for the cohort · **Blocks** = must be resolved before go-live · **Decision** = needs business input.

### 6.1 Recredentialing cycle

| Process (verified class) | Key filter | Network-only | Full term | Verdict |
|---|---|---|---|---|
| `Account.PRM_IsReCredDue__c` | **Formula checkbox**: `AND(PRM_ReCredDueDate__c > TODAY(), PRM_ReCredDueDate__c - TODAY() <= 180)`. Not Apex-writable | Still true — clock intact | **Permanently false** — due date nulled | **Allow** / **Blocks** |
| `PRM_CheckCAQHAccessOnDueAccountsBatch` (self-scheduled) | `Account.isActive = true AND RecordTypeID = pract AND PRM_DelegatedOnly__c = false AND PRM_PNC__c = false AND PRM_ReCredDueDate__c = <date/range>` | Fires | **Silently stops** (both `isActive` and the due date fail) | **Allow+Honor** / **Blocks** |
| `PRM_RecredSendEmailOnDueAccountsBatch` (chained from above, day 1) | `Account.isActive = true AND PRM_ReCredDueDate__c = THIS_MONTH` | Fires — practitioner gets a recred email while the group is being negotiated | Stops | **Decision** (Q9) — correct process, awkward optics |
| `PRM_RecredCAQHDueNotificationBatch` | CM `Status = CAQH Action Needed`, `Stage IN (App Review, PSV)`, `PRM_CAQHAccessible__c = false`, `Account.IsActive = true` | Fires | Stops | **Allow+Honor** |
| `PRM_ReCheckActiveCAQHValidationBatch` + `PRM_ReCheckActiveCAQHValidtnScheduler` | CM `Status = CAQH Access`, `Stage = App Review`, `Account.IsActive = true` | Fires | Stops | **Allow+Honor** |
| Recred due-date computation | `PRM_PARReCredCommitteeReviewBatch` sets `PRM_ReCredDueDate__c` on approve (+3 years) | Correct — new cycle starts | Nulled at term, **never restored by reinstate** | **Allow** / **Blocks (R2)** |
| `PRM_PARReCredCommitteeReviewBatch`, `PRM_PARReCredCommitteeReviewDenialBatch` | `IndividualApplication WHERE Id IN <caller list>` — no status/active filter | Fires (Id-scoped) | **Also fires** — a fully-termed practitioner can still be committee-approved | **Allow+Honor** / **Blocks** |
| **RCAT** — `PRM_ReviewRCAT_English` **v8**, `PRM_RCATProcessingService`, `PRM_RCATLocationTerminationBatch`, `PRM_RCATNetworkTerminationBatch` | Load: IA `Status = Pending Closure`, `PRM_RecredTerm__c = TRUE`, ReCred RT, Person Account | **Fires — a soft-termed practitioner who goes recred-non-compliant is genuinely terminated, and a `PRM_Letter__c` RT `PRM_Termination` is mailed, mid-negotiation** | Fires | **Blocks (R4)** |
| ReCred → Initial Cred conversion | `PRM_ReCredToInitialCredConversion__c` **does not exist as a field**; conversion is a **manual PSV Yes/No**, not an elapsed-time rule (`ReCred_to_InitialCred_Conversion_Plan.md`) | No automatic conversion — the feared surprise **does not fire automatically** | Same | **Allow, no action** — but see Q10 |

**Correction to a premise in the prompt.** The prompt flags "does two months of non-participation push a practitioner out of compliance, converting their recred into an initial cred on reinstatement? This is the single most likely business surprise." Grounded answer: **there is no automatic conversion mechanism.** The conversion plan drives entirely off a manual PSV specialist answer ("Is practitioner out of compliance or past due for ReCred?"), the field is not deployed, and no batch flips it. The real surprise is different and worse: **`PRM_ReCredDueDate__c` is nulled by termination and never restored, so a reinstated practitioner has no recred clock at all** — they are not converted to Initial Cred, they simply fall out of the recred population silently, and `PRMLoadOffCycleCaseCaseMgrReinstate_1` stamps them `Credentialed` on the way back in.

### 6.2 Verification, compliance, monitoring

| Process (verified class) | Key filter | Network-only | Full term | Verdict |
|---|---|---|---|---|
| `PRM_PractitionerPSVBatch` + `PRM_PractitionerPSVBatchScheduler` | `Id IN (InfoCode 'IBC Professional Staff') AND isActive = true AND PRM_ReCredDueDate__c = <future date>` | Fires | Stops | **Allow+Honor** |
| `PRM_PractitionerPNCBatch` | `Id IN :practitionerAccountIds AND PRM_BypassPNC__c = false AND RecordType = pract` — **no `IsActive` filter**; downstream HCPF read uses `IsActive = true` | Fires | **Also fires** | **Allow** |
| `PRM_PractitionerPNCDailyBatch` + scheduler | `HealthcareFacility WHERE PRM_ProcessPNC__c = true AND PRM_IsErrorRecord__c = false`; execute uses HCPF `IsActive = true` | Fires | Fires | **Allow** |
| `PRM_CreateAdverseActionNpdbBatch` | Iterable from an OmniScript input map — no status SOQL | Only if a human runs it | Same | **Allow** |
| `PRM_OrgNPDBProcessorBatch` (self-scheduled) | `SELECT Id FROM IndividualApplication` + Custom Metadata `RecordIds__c` / `Query_Condition__c` | **Depends on MDT config — UNVERIFIED** | Same | **Decision** — inspect the MDT rows before go-live |
| `PRM_ReinitiateNPDBReport` + `PRM_ReinitiateNPDBReportScheduler` | CM `RecordType.DeveloperName IN (PAR, ReCred) AND PRM_Stage__c IN (PSV, QC Review)` — **no `Account.IsActive`** | Fires | **Also fires** | **Allow+Honor** |
| License / DEA / board-cert expiry during window | Held on `Identifier__c`, `BoardCertification` (`TerminationDate`, `TerminationReason`), expiries surfaced through PSV | Normal — records untouched | Records already effective-dated closed by the cascade | **Allow+Honor** / **Blocks** |
| CAQH attestation expiry | Via the CAQH batches above | Fires | Stops | **Allow+Honor** |
| Sanctions / exclusion / CMS preclusion | `PRM_FlowCMSPreclusionLetter` (`@InvocableMethod`, flow-driven) — creates Case (PDA Termination) + IA + `PRM_Letter__c` RT `PRM_Preclusion` | Fires — and correctly so; a preclusion during the window is a **real** for-cause event that must override the soft term | Fires | **Allow — must override** (Q11) |

### 6.3 Correspondence

The US-7 matrix in `ReCred_to_InitialCred_Conversion_Plan.md` is the right template; this is the same exercise for the soft-term window.

| # | Communication | Type | Recipient | Trigger / mechanism (verified) | Network-only | Verdict |
|---|---|---|---|---|---|---|
| 1 | ReCred final notice | Email (SendGrid) | Practitioner | CAQH validation in App Review via IP `PRM_ValidateCAQHAppReview`. **Note: `PRM_sendGridNotifications` and `PRM_SendGridRecredTemplateIBC` do NOT exist as classes** — actual sender is `PRM_SendGridEmailProcessor` with `PRM_GlobalConstant.SENDGRID_RECRED_TEMPLATE` | Fires — "failure to respond → voluntary withdrawal, 10 business days" reaches a practitioner whose group is mid-negotiation | **Decision (Q9)** |
| 2 | ReCred due-date monthly email | Email (SendGrid) | Practitioner | `PRM_RecredSendEmailOnDueAccountsBatch`, 1st of month | Fires | **Decision (Q9)** |
| 3 | Welcome letter | `PRM_Letter__c` RT `PRM_Welcome` | Practitioner | `PRM_LetterWelcomeBatch` + `PRM_LetterWelcomeScheduler` — HCPF RT `PRM_PractitionerLocationAffiliation`, CM RT `PRM_PractitionerParticipationRequest`, `Stage IN (PDA Review And Update, Network Management QC, Complete)`, `Status = Approved`, `PRM_AsyncProcess__c = NULL`. **No `IsActive` filter** | Fires for in-flight PARs | **Allow** |
| 4 | **Termination letter** | `PRM_Letter__c` RT `PRM_Termination` | Practitioner | RCAT only — `PRM_ReviewRCATLoad` → `PRM_RecredTerminationLetterParent` (**v2** active) | **Does NOT fire from the soft term itself** — no letter is generated by an HFN-only termination. It fires only if RCAT catches someone (R4) | **Allow — but resolve R4** |
| 5 | CMS preclusion letter | `PRM_Letter__c` RT `PRM_Preclusion` | Practitioner / facility | `PRM_FlowCMSPreclusionLetter` | Fires | **Allow — must override** |
| 6 | ReCred letters | `PRM_Letter__c` | Practitioner | `PRM_LetterRecredBatch` + `PRM_LetterRecredScheduler` — CM `Category = Credentialing`, RT `Re-Credentialing`, `(Status IN (In Progress, Pending NPDB) AND Stage = PSV) OR (Status = Pending CAQH Access AND Stage = App Review)`, `PRM_AsyncProcess__c = NULL`. **No `Account.IsActive` filter** | Fires | **Allow+Honor** |
| 7 | Reinstatement correspondence | — | — | **Nothing exists.** No `PRM_Letter__c` record type, batch, or SendGrid template for reinstatement | Does not fire | **Decision (Q9)** — recommend none for a soft term, since from the practitioner's perspective their credentialing never lapsed |
| 8 | Internal bell / email | In-app + email | Internal users, queues | `PRM_NotificationHelper.sendBellNotification()` / `sendEmailNotification()`; `PRM_ReinstateVendorAccountBatch` sends a bell on completion | Fires | **Allow** |

**The good news on the prompt's letter question:** "will a termination letter be mailed to every practitioner in the group?" Under Candidate A, **no** — termination letters are generated only from the RCAT path, not from a network-participation change. Under Candidate C the answer depends on whether the vendor/practitioner termination flows are wired to letters (they are not, on the evidence: `PRM_Letter__c` RT `PRM_Termination` is produced by `PRM_RecredTerminationLetterParent` from RCAT). A suppression switch is therefore **not required** for the recommended construct — but the RCAT path must be fenced (R4). **Q3** remains, because regulatory network-termination notice is a separate obligation from these letters and likely lives outside Salesforce.

### 6.4 Activation / effectivity engines

| Process (verified class) | Key filter | Network-only | Verdict |
|---|---|---|---|
| `PRM_FutureDatedProcessingBatch` + `PRM_FutureDatedProcessingBatchScheduler` / `PRM_FutureDatedProcBatchSchActivation` / `PRM_FutureDatedProcBatchSchTermination` | `PRM_Processed__c = FALSE AND PRM_EffectiveDate__c = TODAY AND PRM_Status__c = 'Activate' \| != 'Activate' AND PRM_SObjectRecordId__c != NULL` | Fires. **Pre-existing FDP rows for the cohort's HFNs will apply their staged dates during the window** — must be reconciled | **Blocks** |
| `PRM_PractitionerActivationBatch` | `Account WHERE Id IN :accountIds` — no status filter | Only if invoked | **Allow** |
| `PRM_FutureAddressActivateBatch` (self-scheduled) | `Address WHERE (PRM_EffectiveFrom__c = today OR PRM_EffectiveTo__c = today)` | Fires; addresses untouched by A | **Allow** |
| `PRM_FutureHCProviderNPIActivateBatch` (self-scheduled) | `PRM_HealthcareFacilityNPI__c WHERE PRM_EffectiveFrom__c = TODAY` | Fires | **Allow** |
| `PRM_UpdateEffectiveDateBatch` | `HealthcareFacility WHERE Id IN :facilityIds AND PRM_Active__c = true` | Fires; facility stays active under A | **Allow** |
| `PRM_HFNCascadeBatch` | HFN `RT = PRM_FacilityPractitionerTxNw AND HealthcareFacilityId = :facilityId AND (PRM_FacilityNetworkEffectiveToday__c = true OR PRM_Pending__c = true OR (PRM_Pending__c = false AND PRM_IsErrorRecord__c = false AND EffectiveFrom > today))` | **Directly touches the objects A terminates** — could re-cascade HFN rows back in | **Blocks** |
| `PRM_UpdateHCFNetworkBatch` | HFN `WHERE PayerNetworkId IN :payerNetworkIds AND HealthcareFacilityId = :facilityId AND RT = PRM_FacilityPractitionerTxNw` — **no `IsActive` filter** | Same exposure — a payer-network date change during the window would rewrite terminated rows | **Blocks** |

**Stale FDP rows are a real, documented hazard, not a hypothetical.** `FutureDated_Termination_PushOut_UnitTest_Scenarios.md` scenario **F3** ("push out then reinstate") explicitly records that FDP cleanup after reinstatement is **out of scope**, and **N4** flags that upserting over an already-processed FDP row (`PRM_Processed__c = true`) may reset it. `PRM_FutureDatedProcessingBatchHandler.deleteRedundentRecords()` only cleans rows where `EffectiveDate <= TODAY`. **Any soft-term design must include an explicit FDP reconciliation step** at both term and reinstate.

### 6.5 Other lifecycle events during the window

| Event | Network-only | Verdict |
|---|---|---|
| Off-cycle changes (name, address, role, specialty/taxonomy, new region) | Submittable — Account and HCPF are active. Changes apply to live records and survive to reinstatement automatically | **Allow+Honor** |
| PDM manual updates | `PRM_PDMManualChanges_English` (active **v9**) works normally. `PRM_ManualUpdatePracLocTerminationBatch` and `PRM_ManualUpdatesCrossRefBatchHelper` both call the **Non-Par branch** of `setTermDataPractitioner` → **a routine PDM location termination during the window will null the practitioner's recred due date** | **Blocks** — independent of the soft term, but the window multiplies the exposure |
| `PRM_ProvChangeTerminationBatch` | `HealthcareFacility WHERE Id = :facilityId` — no status filter | **Allow** |
| `PRM_ProvChangePDAPASBatch` | `HealthcareFacilityNetwork WHERE Id IN :allIds` — **writes HFN, no status filter** | **Blocks** — same object A terminates |
| New initial cred for this group during the window | Nothing blocks it. New practitioner joins a group that is commercially out of network | **Decision (Q6)** |
| Delegated roster files arriving mid-window (adds / changes / terms) | Vendor keeps sending. Adds land participating (§4.2) | **Decision** |
| Ancillary reassessment — `PRM_CheckDueOnAncillaryReAssessmentBatch` (self-scheduled) + `PRM_NotifyReAssessmentDueDateBatch` | `PRM_AncillaryAssessment__c WHERE PRM_Account__r.RecordTypeId = vendor AND PRM_Account__r.IsActive = true AND PRM_AuthorizedSignatureForProvider__c != NULL AND PRM_ReAssessmentDueDate__c ...` | **Allow** under A (vendor stays active); **stops** if the vendor Account is termed | **Allow** / **Blocks** |

### 6.6 Downstream interfaces and consumers

| Interface (verified class) | Key filter | Exposure | Verdict |
|---|---|---|---|
| `PRM_CrossRefBatch` | HCPF `HealthcareFacilityId IN :map AND RT IN (PRM_PractitionerLocationAffiliation, PRM_AdmittingPrivileges) AND IsActive = TRUE` | Reads HCPF (untouched by A) | **Allow** |
| `PRM_AccountCreationCrossRefBatch`, `PRM_ManualUpdatesCrossRefBatch` | `HealthcareFacility WHERE Id IN :facilityIds` — no status filter | Their helpers call the **Non-Par branch** → recred-clock exposure | **Blocks** |
| `PRM_CMACreationBatch` | `HealthcareFacilityNetwork WHERE Id IN :hfnIds` | Writes/reads HFN | **Decision** |
| `PRM_CMAProviderChangeBatch` | IA `Stage != Complete AND PRM_UseCaseManagerAssociation__c = false AND RT = Provider Change Request AND PRM_ActionType__c INCLUDES (...)` | Open CMs only | **Allow** |
| `PRM_ParFormCmaBatch` | dynamic `WHERE PRM_CaseManager__c = :cmId` | Case-scoped | **Allow** |
| `PRM_PASUpdateBatch` | `HealthcareFacilityNetwork WHERE Id IN :hfnIds` | **Writes HFN** — PanelStatus updates could resurrect terminated rows | **Blocks** |
| `PRM_NCPDPBatch` (self-scheduled) | aggregates with `PRM_Active__c = TRUE` on identifiers/addresses | Untouched by A | **Allow** |
| Roster sync — `PRM_UPHSRosterRecordsSyncBatch`, `PRM_UPennRosterRecordsSyncBatch`, `PRM_AsyncProcess__c`, `NetworkMember`, `NetworkMemberChunk` | UPenn: `PRM_RosterAttestationStaging__c WHERE PRM_Status__c = :status AND PRM_Source__c = :source AND PRM_ProcessingDate__c = null` | **These are named for specific systems (UPHS, UPenn).** If the negotiating group is one of them, this is in scope; otherwise not | **Decision (Q4)** |
| **Provider directory publication / member-facing search** | **UNVERIFIED — no publication component found in this repo** | **The gating unknown (R1, Q1)** | **Blocks** |
| **Claims eligibility, member PCP panel assignment, capitation site assignment** | **Out of Salesforce.** No component in this repo performs member reassignment | Members may be reassigned away during the window and **that is very likely not reversible by anything in this system** | **Blocks — out-of-Salesforce dependency (Q2, R? see §10)** |
| Ghost-practitioner consistency (`Account.IsActive` before/after children) | `PNM_Reinstate_Apex_Service_Architecture.md` §3.2 | **Not applicable under A** — `IsActive` never flips | **Allow, no action** |

### 6.7 Summary of the inventory

| Verdict | Count | The ones that matter |
|---|---|---|
| **Allow, no action** | 16 | Most of the cascade is simply untouched under Candidate A |
| **Allow + Honor** | 8 | The recred/CAQH/PSV/letters chain — these firing correctly *is* the requirement |
| **Blocks — must resolve** | 9 | RCAT (R4); FDP staged rows; `PRM_HFNCascadeBatch`; `PRM_UpdateHCFNetworkBatch`; `PRM_ProvChangePDAPASBatch`; `PRM_PASUpdateBatch`; the Non-Par-branch callers (`PRM_ManualUpdatePracLocTerminationBatch`, `PRM_CrossRefBatchHelper`, `PRM_ManualUpdatesCrossRefBatchHelper`); directory read; member reassignment |
| **Needs business decision** | 7 | Q4, Q6, Q7, Q8, Q9, Q10, Q11 |
| **Suppress during window** | 0 | Notably: **nothing needs suppressing under Candidate A.** That is the strongest evidence for the recommendation |

The five "Blocks" rows that write `HealthcareFacilityNetwork` without an `IsActive` guard — `PRM_HFNCascadeBatch`, `PRM_UpdateHCFNetworkBatch`, `PRM_ProvChangePDAPASBatch`, `PRM_PASUpdateBatch`, `PRM_CMACreationBatch` — are the real technical risk of Candidate A, because they can silently un-terminate the cohort. This is why the cohort marker in §8 must be a field those batches can be taught to respect, not just a report filter.

---

## 7. Reinstatement via delegated file upload

### 7.1 Does the roster support reinstatement? No — quantified schema delta

**Confirmed against the full catalog.** `PRM_DelegatedRoster_CommonSchema.md` v1.1 operation catalog: `CREATE`, `CREATE_GROUP`, `ADD_TO_LOCATION`, `ADD_TO_ALL_LOCATIONS`, `REMOVE_FROM_LOCATION`, `TERM_NETWORK`, `CHANGE_DEMOGRAPHIC`, `CHANGE_SPECIALTY`, `CHANGE_GROUP`, `CHANGE_TIN`, `CHANGE_ADDRESS`, plus `EXCEPTION` (a status, not an operation). The template's `Request Type` dropdown mirrors it with `CREATE_PROVIDER` in place of `CREATE`. **No `REINSTATE`, `REACTIVATE`, or `UNTERM` anywhere.** The schema is also explicit that `recordsToUpdate` is *"CREATE/ADD only"*, and the file-upload design plan's backend target is `PRM_PractitionerCreationContainer` → `PRM_DelegatedPractitionerCreation_Procedure_6`, i.e. a **creation** IP.

**Minimum schema delta for Candidate A:**

| Layer | Delta |
|---|---|
| Operation catalog | Add **`REINSTATE_NETWORK`** (naming it for the scope, mirroring `TERM_NETWORK`, rather than a generic `REINSTATE` that would imply the 150–300-row practitioner reinstate) |
| Envelope | Add `reinstatement` block mirroring `termination`: `scope` (`NETWORK` initially; `AFFILIATION`/`GROUP`/`CONTRACT` reserved), `reinstateDate`, `reason`, `networkTargets[]`, `originalTermDate` (for reconciliation), and `periodHandling` (`NEW_ROW` \| `REOPEN`, per §5.4) |
| Template | Add `REINSTATE_NETWORK` to the `Request Type` dropdown; add `Reinstate Date` and `Reinstate Scope` to the 15-column control block; reuse the existing `Network(s)`, `Contract / PO`, `Practitioner Ref`, `Group Ref` columns |
| Backend | The design plan routes to a creation IP. Reinstatement needs a different lane — extend `PRM_UpdateHCFNForReInstate` (§5.4) rather than reuse `PRM_ReinstateVendorAccountBatch`, which is vendor-account-shaped and hardcoded to batch size 5 |

**ASSUMPTION:** business intends the reinstatement file to be *their own* roster file re-submitted, not a system-generated one. If the reinstatement set can instead be **derived** from the cohort marker (§8), the roster delta becomes optional for the pilot — which is a materially cheaper path and worth putting to business as **Q4a**.

### 7.2 Reconciliation rules

The reinstatement file will not match the terminated cohort. Recommended handling, all of which depends on the cohort marker existing:

| Case | Recommended handling |
|---|---|
| In file, not terminated | Route to exception, do not process. Under A this is detectable — the HFN row has no soft-term marker |
| Terminated, not in file | **Leave terminated** and report. Do not auto-reinstate: a practitioner omitted from the vendor's return file has most likely genuinely left |
| In file with changed data (new address, specialty, group NPI) | **Split**: reinstate the network participation, and route the change to the normal off-cycle/PDM lane. Do **not** let a reinstatement file become a backdoor mass update — that would bypass QC |
| Duplicates in file | Reject at validation (the file-upload plan already does in-file NPI dedup) |
| Practitioner moved to a different group | Exception. Their HCPF affiliation to *this* group must be verified active before reinstating this group's network rows (§4.2) |
| Reinstate before the term even applied (future-dated) | Cancel the staged FDP `Terminate` row instead of reinstating. **Cancel is explicitly not built** — this is net-new work |

### 7.3 Volume and async posture

**Sizing is unknown and must come from business (Q12 in effect — folded into Q4).** Order-of-magnitude estimate for a mid-size delegated group: 200–800 practitioners × 1–5 locations × 2–6 networks → **roughly 1,000–15,000 HFN rows**.

**The async framework the prompt assumes does not exist.** `PRM_AsyncJob__c`, `PRM_AsyncJobDetails__c`, and `PRM_AsyncJobRecords__c` are **absent from `objects/`** — `CLAUDE.md` Epic A is unbuilt. `PRM_AsyncJobRequest__c` / `PRM_AsyncJobQueued__e` / `PRM_SubmitAsyncJob` / `PRM_AsyncJobDispatcher` / `PRM_MassAddNetworkBatch` / `prmMassUpdateHub` are also absent. What exists: `PRM_AsyncProcess__c` (7 fields, no lookups), `PRM_FailedRecordStaging__c`, `PRM_ExceptionLogger`.

**Recommended posture — do not wait for the async framework.** At 1,000–15,000 single-object rows this is a **plain `Database.Batchable`** job with `Database.Stateful`, scope 200, following the `PRM_RCATNetworkTerminationBatch` / `PRM_UpdateHCFNForReInstate` pattern that already exists and already writes failures to `PRM_FailedRecordStaging__c`. One bulk DML per object type; one object type. **Explicitly do not reuse `PRM_ReinstateVendorAccountBatch`** — it is vendor-account-shaped, ~600 LoC, `Database.Stateful`, and hardcoded to `Database.executeBatch(batch, 5)` from `PRM_ReinstateCallable`; at cohort scale a batch size of 5 means thousands of chunks against the Flex Queue's 100-concurrent cap.

**Idempotency and double-upload.** Guard on state, not on job identity: skip any HFN row that is already active with `EffectiveFrom >= reinstateDate`, and match on `(PractitionerId, HealthcareFacilityId, PayerNetworkId, RecordTypeId)` plus the cohort marker. Under the `NEW_ROW` model (§5.4) a double upload without this guard creates duplicate participation periods — the worst possible outcome for claims. Failures land in `PRM_FailedRecordStaging__c` for triage and re-run.

**Case Manager volume.** The existing pattern creates one `Case` + one `IndividualApplication` per reinstate submission. At 200–800 practitioners that is hundreds of Case Managers. Recommended default: **one Case Manager for the whole soft-term action and one for the whole reinstatement**, with per-practitioner traceability carried by `HealthcareFacilityNetwork.PRM_CaseManager__c` (the field already exists and both the RCAT termination and HFN reinstate batches already stamp it). This needs business and reporting sign-off (**Q13**, folded into Q9) because it changes what a Case Manager means for this cohort.

---

## 8. Audit, reporting, monitoring

### 8.1 How an auditor proves continuous credentialing across the window

**Under Candidate A the answer is clean:** `Account.PRM_CredentialingStatus__c` never left `Credentialed`, `PRM_ReCredDueDate__c` was never nulled, the `HealthcarePractitionerFacility` affiliation row has an unbroken `EffectiveFrom`/`EffectiveTo`, and any recred that came due during the window has its own `IndividualApplication` with a normal outcome. The credentialing record *is* the proof, because it was never disturbed. The network gap is separately and deliberately evidenced by the closed `HealthcareFacilityNetwork` rows.

Under B or C there is **no** such proof — the cred status says `Terminated` for two months and then says `Credentialed` because a DataMapper hardcodes that literal.

### 8.2 The distinguishing marker — recommended mechanism

A marker is required, for four jobs: find the cohort, exclude it from the HFN-writing batches in §6.4/§6.6, reinstate it as a set, and report on it.

**Recommendation — reuse, no new object:**

| Marker | Mechanism | Justification against reuse |
|---|---|---|
| **Primary** | **`HealthcareFacilityNetwork.PRM_TerminationReason__c`** = a new picklist value, e.g. `Contract Negotiation` | The field **already exists** on HFN and is already the system of record for why a network row closed. Adding a picklist value is the smallest possible change. **Critical:** this value must **not** be added to `PRM_GlobalConstant.FULLTERMREASON` |
| **Cohort correlation** | **`HealthcareFacilityNetwork.PRM_CaseManager__c`** → the single soft-term `IndividualApplication` | Field exists; both `PRM_RCATNetworkTerminationBatch` and `PRM_UpdateHCFNForReInstate` already stamp it. Gives an exact, queryable cohort with no new object |
| **Run tracking** | **`PRM_AsyncProcess__c`** — `PRM_Type__c` / `PRM_SubType__c` / `PRM_Status__c` / `PRM_ItemsProcessed__c` / `PRM_ItemsFailed__c` | Exists with exactly the right shape. No lookups, so it is operational telemetry only, not the cohort record |
| **DLQ** | **`PRM_FailedRecordStaging__c`** | Already the DLQ for `PRM_UpdateHCFNForReInstate` |
| **Exceptions** | **`PRM_ExceptionLogger.logException(...)`** → `PRM_ExceptionLog__c` / `PRM_ExceptionLogEvent__e` | Org convention (`CLAUDE.md` §6) |

**What must be taught to read the marker** — this is the work, and it is the honest cost of Candidate A: `PRM_HFNCascadeBatch`, `PRM_UpdateHCFNetworkBatch`, `PRM_ProvChangePDAPASBatch`, `PRM_PASUpdateBatch`, `PRM_CMACreationBatch`, and the RCAT entry gate. Each currently writes HFN with no participation-state guard.

**Rejected:** a new `PRM_SoftTermCohort__c` object (nothing would read it that the two existing HFN fields don't already carry) and a new `Account`-level flag (re-introduces the global-blast-radius problem that Candidate A exists to avoid).

### 8.3 Operational monitoring and reports

Monitoring during the window: `PRM_AsyncProcess__c` progress rows; `PRM_FailedRecordStaging__c` triage queue; `PRM_ExceptionLog__c` for the batch runs; and a scheduled reconciliation query proving no cohort HFN row has been silently reactivated by the §6.4/§6.6 batches.

Reports/list views business will need (all buildable on existing objects): cohort roster with current network state; recreds that came due during the window and their outcomes; cohort members whose HCPF affiliation ended during the window (real attrition — do not reinstate); cohort members added during the window (do not reinstate); RCAT candidates in the cohort (the R4 tripwire); reinstatement reconciliation (file vs cohort); and a DLQ aging report. **Note** for the existing `PRM_CaseManagerReportType` and `Case_Manager_with_Accounts` report types: if a single Case Manager covers the whole cohort (§7.3), per-practitioner reporting must come from the HFN rows, not from Case Manager rollups.

---

## 9. Negotiation-outcome matrix

| Outcome | Handling under Candidate A | New work? |
|---|---|---|
| **Full reinstatement** (the planned case) | Reinstate all HFN rows carrying the cohort marker, gated on HCPF affiliation still active | Baseline |
| **Partial — subset of practitioners** | Marker query intersected with the returned list; the rest stay terminated. Reconciliation rules in §7.2 handle it | None beyond baseline |
| **Partial — subset of locations** | Filter by `HealthcareFacilityId`. Naturally supported since the marker is per HFN row | None |
| **Partial — subset of networks** | Filter by `PayerNetworkId`. Naturally supported | None |
| **Different terms — different networks** | Not a reinstatement. Terminated rows stay closed; **new** HFN rows are created for the new networks through the normal add path. Must check closed-network routing (`prmCheckClosedNetworkLogic` + `PRM_ClosedNetworkConfig__mdt`, both cited as existing — **UNVERIFIED in this repo**) | Moderate |
| **Different terms — different effective dates** | `reinstateDate` is a parameter; `resolveEffectivity` handles the arithmetic including the `EffectiveFrom >= date` error case | None |
| **Different terms — different contract/PO** | `ProviderNetworkContractId` on HFN differs → new rows, not reinstatement. Same as "different networks" | Moderate |
| **No reinstatement — soft term becomes real** | **This is where Candidate A shows its second big advantage: nothing has to be undone.** Run the normal Account/PL/Practitioner termination flows with the correct reason code, on the normal cascade, with correct dates. The soft term did not pre-empt or corrupt the real one | None |
| **Extension beyond two months** | **A survives an indefinite window** — there is no pending date to push out, no staged FDP row to go stale, and no expiring construct. Compare Candidate D, where extension means exercising the known-broken push-out path. Watch instead for accumulating drift: recreds completing, licenses lapsing, practitioners leaving | None |
| **Earlier than planned** | Reinstate any time; `reinstateDate` is a parameter | None |

Candidate A is the only construct that handles all nine outcomes without a compensating action.

---

## 10. Risks and mitigations

| # | Risk | Sev | Mitigation |
|---|---|---|---|
| R1 | Directory/member search may read `Account.IsActive`, so network-only termination may not remove the cohort from the published directory | **Critical** | **Answer Q1 before design.** Trace the directory publication path end-to-end. Fallback in §3.2 |
| R2 | `setTermDataPractitioner` nulls `PRM_ReCredDueDate__c` on **both** branches; no reinstate path restores it | **Critical** | Candidate A avoids the code path entirely. If B/C is chosen, a snapshot object plus a restore step is mandatory and must be in the estimate. Independently: raise the PDM/cross-ref Non-Par callers (§6.5, §6.6) as a **standalone defect** |
| R3 | Reinstate hardcodes `PRM_CredentialingStatus__c = 'Credentialed'` in `PRMLoadOffCycleCaseCaseMgrReinstate_1` | High | Candidate A never calls it. Otherwise the value must be derived, not defaulted. Raise as a standalone defect |
| R4 | RCAT can genuinely terminate cohort members mid-window and mail `PRM_Letter__c` RT `PRM_Termination` during negotiation | High | Fence the RCAT entry gate on the cohort marker (`PRM_ReviewRCAT_English` v8 load / `PRM_RCATProcessingService`), or hold `PRM_RecredTerm__c` for the cohort. Needs a decision (Q11) |
| R5 | Five HFN-writing batches have no participation-state guard and can silently reactivate terminated rows | High | Teach each to respect the cohort marker (§8.2); add a scheduled reconciliation check |
| R6 | Members reassigned away from cohort practitioners (PCP panels, capitation) — likely irreversible and outside Salesforce | High | Out-of-Salesforce dependency. Escalate to whoever owns eligibility/enrolment **before** September. No mitigation available in this codebase |
| R7 | Stale/duplicate `PRM_FutureDatedProcessing__c` rows fire during or after the window on wrong dates; push-out is a known live defect; cancel is not built | High | Explicit FDP reconciliation at term and reinstate. Do **not** build on Candidate D until the push-out defect is fixed |
| R8 | Retroactive-dating claims exposure if Q2 is answered "retroactive continuity" | High | Recommended default is a gap (§5.3). Require named sign-off for retroactive |
| R9 | Regulatory network-termination notice obligations, and directory accuracy during the window | High | Compliance question, not technical. Q3 |
| R10 | Reinstatement mechanism doesn't exist: no roster REINSTATE op, roster upload LWC/Apex unbuilt, `PRM_AsyncJob__c` framework unbuilt | High | Derive the reinstatement set from the cohort marker instead of a file (Q4a); use a plain Batchable (§7.3). Do not make September depend on three unbuilt layers |
| R11 | Cohort query wrong → blast radius is the whole vendor group or, via the shared practitioner `Account`, practitioners at *other* groups | High | Candidate A confines writes to HFN rows filtered by this group's facilities. Mandatory dry-run: produce and have business sign off the cohort list before any DML |
| R12 | Two OmniStudio IP versions active simultaneously (`PractitionerTerminationRecordsUpdate` v25 **and** v26; `FetchPractNPIForTermination` v2 **and** v3) | Medium | Pre-existing hygiene issue. Resolve before touching those paths |
| R13 | `lastManStanding` cascading the practice locations and the group out from under the cohort | Medium | Does not fire under A (HCPF untouched). Add an explicit regression test asserting it |
| R14 | P2P `EffectiveFrom`/`EffectiveTo` drift; the corrective helper is unbuilt and its feature flag defaults off | Medium | Not triggered by A. Would be material under B/C at cohort scale |
| R15 | Governor limits — 1,000–15,000 HFN rows | Low–Med | Plain Batchable, scope 200, one bulk DML per object type. Avoid `PRM_ReinstateVendorAccountBatch`'s batch size 5 |
| R16 | Two months of non-participation is itself a credentialing-compliance question (does an interrupted network participation break a credentialing cycle?) | Medium | Compliance question. Under A, credentialing is demonstrably continuous — which is the strongest available answer |

---

## 11. Open questions for business

Each has a recommended default so business can approve rather than compose.

**Q1 — Does the provider directory / member-facing search determine "in network" from network participation rows, or from `Account.IsActive`?**
*Why it matters:* gates the entire recommendation. If the directory reads `Account.IsActive`, network-only termination will not remove these practitioners from the published directory, and business's commercial objective is unmet.
*Options:* (a) network participation → Candidate A works as designed; (b) `Account.IsActive` → Candidate A plus a dedicated suppression flag; (c) both/unknown → trace before design.
*Recommended default:* **treat as (c) and trace it first.** This is a one-day investigation that de-risks the whole project.

**Q2 — For the two-month window, is the intent a gap in network participation, or retroactive continuity?**
*Why it matters:* different claims-adjudication, directory-accuracy, and audit outcomes. Retroactive continuity makes two months of adjudicated claims retrospectively wrong.
*Options:* (a) gap — participation ends Sep 1, resumes Nov 1; (b) retroactive — reopen as if never terminated.
*Recommended default:* **(a) gap at the network layer, unbroken continuity at the credentialing layer.** Retroactive requires named compliance sign-off.

**Q3 — Are regulatory network-termination notices and any termination correspondence required, and must anything be suppressed?**
*Why it matters:* letters landing on practitioners mid-negotiation is a business-relations problem. Grounded finding: **under Candidate A the system generates no termination letter** (that path is RCAT-only), so no suppression switch is needed in Salesforce — but the regulatory notice obligation is separate and probably lives outside this system.
*Options:* (a) notices out of scope for Salesforce; (b) Salesforce must generate them.
*Recommended default:* **(a)**, with an explicit confirmation that Compliance owns the notice obligation.

**Q4 — Which group, how big, is it delegated, and is it one of the named roster-sync systems (UPHS / UPenn)?**
*Why it matters:* drives sizing, whether roster-sync interfaces are in scope, and whether the reinstatement really must be a file.
*Recommended default:* **delegated, not UPHS/UPenn**, per the prompt's framing — and get the actual counts before estimating.

**Q4a — Must reinstatement be driven by a vendor-supplied file, or may the system derive the reinstatement set from the cohort marker?**
*Why it matters:* the file path requires a roster schema change, template change, and unbuilt upload UI. Deriving from the marker removes all three from the critical path.
*Recommended default:* **derive from the cohort marker for this project**, and treat a roster `REINSTATE_NETWORK` operation as a separate, later enhancement.

**Q5 — Is "Group NPI" the group Account's NPI or the facility/location NPI?**
*Why it matters:* inherited open item (`MassNetworkAddTerminate_TaxIdNpi_UserStories.md` Clarification #6). Wrong join → wrong cohort.
*Recommended default:* **resolve the cohort on Tax ID + vendor Account Id**, and show Group NPI as confirmation only.

**Q6 — Are mid-flight practitioners (PSV, QC, committee, PDA, off-cycle) in the cohort, and may new initial creds be submitted for this group during the window?**
*Recommended default:* **include mid-flight practitioners in the network termination but let their in-flight work run to completion untouched; allow new initial creds to proceed but land them non-participating** so they are not swept into the reinstatement.

**Q7 — Are the group's practice locations themselves out of network, or only the practitioners?**
*Why it matters:* determines whether HFN record types `PRM_FacilityNw` / `PRM_FacilityTx` are in scope alongside `PRM_FacilityPractitionerTxNw`.
*Recommended default:* **include the facility-level network rows** — a group that is out of network is out of network at the location too. Confirm.

**Q8 — Are ancillary / facility / organizational providers under the same TIN in scope?**
*Recommended default:* **exclude from the pilot** and decide separately; they have a different lifecycle (`PRM_AncillaryAssessment__c`, reassessment batches).

**Q9 — During the window, should routine credentialing correspondence keep going to these practitioners, and should reinstatement generate any correspondence?**
*Why it matters:* under Candidate A, recred due-date and final-notice emails **will** be sent, because credentialing legitimately continues. That is correct system behavior and possibly awkward optics. Grounded: no reinstatement correspondence exists today.
*Recommended default:* **keep credentialing correspondence flowing** (suppressing it would break the very continuity business asked for) and **create no reinstatement correspondence** — from the practitioner's perspective their credentialing never lapsed. Includes the Case Manager-volume decision (§7.3): recommended default **one Case Manager for the action, not one per practitioner**.

**Q10 — If a practitioner's recred completes during the window, is that recred valid given they were out of network at the time?**
*Why it matters:* this is the compliance core of "honor what happened." Business said yes; someone in Compliance must own it.
*Recommended default:* **yes, valid** — credentialing and network participation are separate determinations, which is exactly the separation Candidate A makes explicit in the data.

**Q11 — If a cohort practitioner becomes recred-non-compliant, or a real for-cause event occurs (CMS preclusion, sanction), during the window, what happens?**
*Why it matters:* RCAT will otherwise terminate them for real, mid-negotiation, with a letter (R4). Conversely, a preclusion **must** override the soft term.
*Recommended default:* **hold RCAT for the cohort** and route those practitioners to a manual review queue, while **letting genuine for-cause events (preclusion, sanction) proceed unimpeded and permanently exit the cohort.**

---

## 12. Recommended epic / story breakdown

Titles and one-line scopes only, in dependency order. Effort bands are indicative engineer-days, and assume Candidate A. **No stories written in this pass** — authoring must follow `.cursor/skills/user-story-architect/SKILL.md`, with concrete personas (Credentialing Specialist, PDM Specialist, Network Management QC Specialist, Provider Data Admin Specialist), business-language ACs, and a separate `## Technical Implementation (high-level)` section.

| # | Title | Scope | Band |
|---|---|---|---|
| **E0.1** | Directory participation-source spike | Determine whether directory/member search reads network participation or `Account.IsActive`; answer Q1 | 1–2 |
| **E0.2** | Member-impact dependency spike | Confirm with the eligibility/enrolment owners whether PCP panel and capitation reassignment occurs and is reversible (R6) | 1–2 |
| **E0.3** | Cohort dry-run and sign-off | Produce the practitioner/facility/network row inventory for the target group; business signs off before any DML (R11) | 2–3 |
| **E1.1** | Soft-term cohort marker | New `Contract Negotiation` value on `HealthcareFacilityNetwork.PRM_TerminationReason__c`; confirm it is excluded from `FULLTERMREASON`; single soft-term Case Manager stamped to `PRM_CaseManager__c` | 2–3 |
| **E1.2** | Group-scope network termination batch | Batchable over the cohort's HFN rows, reusing `PRM_RCATTerminationBatchHelper.resolveEffectivity`; stamps the marker; DLQ to `PRM_FailedRecordStaging__c`; regression test asserting `lastManStanding` does not fire and `Account`/HCPF/cred fields are untouched | 5–8 |
| **E1.3** | FDP reconciliation at termination | Reconcile / neutralise pre-existing `PRM_FutureDatedProcessing__c` rows for cohort HFNs (R7) | 3–5 |
| **E2.1** | Marker-aware guards on HFN writers | Teach `PRM_HFNCascadeBatch`, `PRM_UpdateHCFNetworkBatch`, `PRM_ProvChangePDAPASBatch`, `PRM_PASUpdateBatch`, `PRM_CMACreationBatch` to respect the cohort marker (R5) | 5–8 |
| **E2.2** | RCAT cohort hold | Fence the RCAT entry gate for cohort members; route to a manual review queue; let for-cause events through (R4, Q11) | 3–5 |
| **E3.1** | Network reinstatement batch | Extend `PRM_UpdateHCFNForReInstate` for the new-period-row model (§5.4); gate on HCPF affiliation active; idempotency guard against double submission | 5–8 |
| **E3.2** | Reinstatement reconciliation | Implement the §7.2 rules: in-file-not-terminated, terminated-not-in-file, changed data, duplicates, moved group | 3–5 |
| **E4.1** | Cohort reports and list views | The seven reports in §8.3 | 2–3 |
| **E4.2** | Operational monitoring | `PRM_AsyncProcess__c` run tracking, `PRM_ExceptionLogger` wiring, DLQ triage view, scheduled silent-reactivation check | 2–3 |
| **E5.1** | Recred-clock defect (standalone) | Fix / decide `setTermDataPractitioner` nulling `PRM_ReCredDueDate__c` with no restore path, and `PRMLoadOffCycleCaseCaseMgrReinstate_1` hardcoding `Credentialed` (R2, R3). **Independent of this project; the window magnifies it** | 5–8 |
| **E5.2** | Duplicate active IP versions | Resolve `PractitionerTerminationRecordsUpdate` v25/v26 and `FetchPractNPIForTermination` v2/v3 both active (R12) | 1–2 |
| **E6.1** | Roster `REINSTATE_NETWORK` operation *(deferrable)* | Schema v1.2 + template column + validation — only if Q4a says the file path is mandatory | 5–8 |

Indicative total for the recommended path excluding E6.1: **~40–65 engineer-days**, with E0.1 and E0.2 as hard gates.

---

## 13. Cross-references

### Workspace documents relied on

| Document | Used for |
|---|---|
| `requirements/SoftTerm_GroupWide_Reinstate_Analysis_Prompt.md` | Scope and required dimensions |
| `requirements/Enhancements/PNM_Reinstate_Apex_Service_Architecture.md` | Three reinstate flows, `ReinstateAs`×`Update` buckets, `PRM_ReinstateVendorAccountBatch`, ghost-practitioner §3.2, duplicate-bucket bug, CPU figures |
| `requirements/Enhancements/practitionerCreation/PRM_DelegatedRoster_CommonSchema.md` | Envelope v1.1, operation catalog, four termination scopes, `lastManStanding`, `endNetworkMembershipsOnly` |
| `requirements/Enhancements/practitionerCreation/PRM_StandardDelegatedRosterImportTemplate.md` | 15 control + 91 data columns, `Request Type` values, termination columns |
| `requirements/Enhancements/practitionerCreation/PractitionerCreation_FileUpload_DesignPlan.md` | Intake design, row-level error handling, ≤200 rows / ≤5 MB, chunking |
| `requirements/RCAT_PracticeLocation_NonPar_FullTerm_Batch_UserStory.md` | Non-Par vs Full-Term, RCAT decision path, `resolveEffectivity` AC-6, `FULLTERMREASON` |
| `requirements/FutureDated_Termination_PushOut_AddressUpdate_UserStory.md` | FDP staging, push-out semantics and defect, cancel out of scope |
| `requirements/FutureDated_Termination_PushOut_UnitTest_Scenarios.md` | 16-object cascade inventory, scenarios F3 / A6 / A7 / N4 / N5 |
| `requirements/MassNetworkAddTerminate_TaxIdNpi_UserStories.md` | Tax ID + Group NPI resolution, network objects, closed-network routing, Clarification #6 |
| `requirements/P2P_EffectiveTo_Override_Scenarios.md`, `requirements/P2P_EffectiveFrom_From_Oldest_Active_PPL_Impact_Analysis.md` | P2P derivation, gaps G1–G5, no-reopen-on-reinstate |
| `requirements/ReCred_to_InitialCred_Conversion_Plan.md` | Conversion trigger (manual PSV, not elapsed time), US-7 communications matrix template |
| `requirements/CloseCase_RecredTerm_PSV_QC_UserStory.md` | `PRM_RecredTerm__c` as the RCAT entry gate |
| `requirements/AccountTermination_PracticeLocationTaxonomy_Typeahead_UserStory.md` | Vendor Account Termination → Non-Par path |
| `docs/implementation-plan/PRM_IBC_HighVolume_TDD.md`, `Epic_C_Async_Framework.md`, `CLAUDE.md` §4.4 / §6 | Async framework design (unbuilt), org conventions, CL-2/CL-3 |

### Components verified in `force-app/main/default/`

**Apex — termination:** `PRM_PractitionerTerminationBatchHelper` (`setTermDataPractitioner`), `PRM_AccountTerminationBatch(Helper|Utility)`, `PRM_PracticeLocationTerminationBatch`, `PRM_PracLocTermHelper`, `PRM_FullPractitionerTerminationBatch`, `PRM_FullPracTermRecredBatchService`, `PRM_ManualUpdatePracLocTerminationBatch`, `PRM_RCATLocationTerminationBatch`, `PRM_RCATNetworkTerminationBatch`, `PRM_RCATTerminationBatchHelper` (`resolveEffectivity`), `PRM_RCATTerminationEffectivityHelper`, `PRM_ProvChangeTerminationBatch`, `PRM_PPLLMSTermService`, `PRM_PDMUnlinkPractitioner`, `PRM_PractitionerDataForVendorTermHelper`, `PRM_GlobalConstant` (`FULLTERMREASON`, `RCATCASETYPE`)

**Apex — reinstate:** `PRM_ReinstateCallable`, `PRM_ReinstateVendorAccountBatch(Helper)`, `PRM_ReinstatePracticeLocationWrapper`, `PRM_ReinstateUtils`, `PRM_UpdateHCFNForReInstate`

**Apex — lifecycle batches (all verified to exist, filters quoted in §6):** `PRM_CheckCAQHAccessOnDueAccountsBatch`, `PRM_RecredSendEmailOnDueAccountsBatch`, `PRM_RecredCAQHDueNotificationBatch`, `PRM_ReCheckActiveCAQHValidationBatch` + `PRM_ReCheckActiveCAQHValidtnScheduler`, `PRM_PARReCredCommitteeReviewBatch`, `PRM_PARReCredCommitteeReviewDenialBatch`, `PRM_PractitionerPSVBatch` + scheduler, `PRM_PractitionerPNCBatch`, `PRM_PractitionerPNCDailyBatch` + scheduler, `PRM_CreateAdverseActionNpdbBatch`, `PRM_OrgNPDBProcessorBatch`, `PRM_ReinitiateNPDBReport`, `PRM_FlowCMSPreclusionLetter`, `PRM_LetterRecredBatch` + scheduler, `PRM_LetterWelcomeBatch` + scheduler, `PRM_NotificationHelper`, `PRM_FutureDatedProcessingBatch` + `PRM_FutureDatedProcessingBatchScheduler` / `PRM_FutureDatedProcBatchSchActivation` / `PRM_FutureDatedProcBatchSchTermination`, `PRM_FutureDatedProcessingBatchHandler`, `PRM_FutureDatedProcessingUtil`, `PRM_PractitionerActivationBatch`, `PRM_FutureAddressActivateBatch`, `PRM_FutureHCProviderNPIActivateBatch`, `PRM_UpdateEffectiveDateBatch`, `PRM_HFNCascadeBatch`, `PRM_UpdateHCFNetworkBatch`, `PRM_ProvChangePDAPASBatch`, `PRM_CheckDueOnAncillaryReAssessmentBatch`, `PRM_NotifyReAssessmentDueDateBatch`, `PRM_CrossRefBatch(Helper)`, `PRM_AccountCreationCrossRefBatch`, `PRM_ManualUpdatesCrossRefBatch(Helper)`, `PRM_CMACreationBatch`, `PRM_CMAProviderChangeBatch`, `PRM_ParFormCmaBatch`, `PRM_PASUpdateBatch`, `PRM_NCPDPBatch`, `PRM_UPHSRosterRecordsSyncBatch`, `PRM_UPennRosterRecordsSyncBatch`, `PRM_ExceptionLogger`, `PRM_SendGridEmailProcessor`, `PRM_OmniProcessUtils(Helper)` (`lastManStandingValidation`), `PRM_ActiveLocationsControllerHelper`, `PRM_RCATProcessingService`, `PRM_RCATProcessingController`

**Objects:** `Account` (RT `PRM_Vendor`; `HealthCloudGA__TaxId__c`, `PRM_CredentialingStatus__c`, `PRM_ParticipationStatus__c`, `PRM_NonParticipatingStartDate__c`, `PRM_TerminationReason__c`, `PRM_ReCredDueDate__c`, `PRM_IsReCredDue__c`, `PRM_EffectiveTo__c`, `IsActive`, `PRM_PNC__c`, `PRM_DelegatedGroup__c`), `HealthcareFacilityNetwork` (RTs `PRM_FacilityNw` / `PRM_FacilityTx` / `PRM_FacilityPractitionerTxNw` / `PRM_TaxonomyNetworkException`; fields per §2.3), `HealthcarePractitionerFacility` (RTs `PRM_PractitionerPracticeAffiliation` / `PRM_PractitionerLocationAffiliation` / `PRM_AdmittingPrivileges`), `HealthcareFacility` (`PRM_NonParLocation__c`, `PRM_NonParticipatingStartDate__c`, `PRM_NpiId__c`, `PRM_CountOfActivePractitioners__c`), `HealthcareProviderNpi`, `IndividualApplication`, `PRM_CaseDataManager__c`, `PRM_FutureDatedProcessing__c`, `PRM_FailedRecordStaging__c`, `PRM_ExceptionLog__c` + `PRM_ExceptionLogEvent__e`, `PRM_AsyncProcess__c`, `NetworkMember`, `NetworkMemberChunk`, `PRM_Letter__c` (RTs `PRM_Termination` / `PRM_Welcome` / `PRM_Preclusion`)

**OmniStudio (active versions):** OmniScripts `PRM_PractitionerReinstateForm_English_9`, `PRM_PracticeLocationReinstate_English_6`, `PRM_PractitionerReinstateVendorForm_English_5`, `PRM_ReinstateLinkExistingPractitioner_English_1`, `PRM_AccountTerminationForm_English_9`, `PRM_PracticeLocationTermination_English_18`, `PRM_PractitionerTerminationForm_English_31`, `PRM_PractitionerTerminationRecredForm_English_4`, `PRM_ReviewRCAT_English` v8, `PRM_PDMManualChanges_English_9`; IPs `PRM_ReinstateRecordCreation_Procedure_4`, `PRM_ReinstatePracticeLocation_Procedure_8`, `PRM_PractitionerReinstateVendorUpdate_Procedure_6`, `PRM_AccountTermination_Procedure_17`, `PRM_PracticeLocationTermination_Procedure_11`, `PRM_PractitionerTerminationRecordsRecredUpdate_Procedure_11`, `PRM_RecredTerminationLetterParent_Procedure_1`; DataMappers `PRMLoadOffCycleCaseCaseMgrReinstate_1`, `PRMDRToUpdateRecordsAfterReInstate_1`, `PRMDRPractitionerAccountUpdate`, `PRMReinstatehealthcareFacilityUpdate`, `PRMReinstateInfoCodeAssignmentUpdate`

### Marked UNVERIFIED / not present

`PRM_sendGridNotifications` · `PRM_SendGridRecredTemplateIBC` / `_AH` · `PRM_ReCredToInitialCredConversion__c` · `PRM_AsyncJob__c` / `PRM_AsyncJobDetails__c` / `PRM_AsyncJobRecords__c` · `PRM_AsyncJobRequest__c` / `PRM_AsyncJobQueued__e` / `PRM_SubmitAsyncJob` / `PRM_AsyncJobDispatcher` · `PRM_MassAddNetworkBatch` / `PRM_MassRemoveNetworkBatch` / `prmMassUpdateHub` · `prmRosterUpload` / `prmRosterGrid` / `PRM_RosterEnvelopeBuilder` / `PRM_RosterValidator` / `PRM_RosterSubmitController` / `PRM_RosterCreationQueueable` · `PRM_ReinstateStatus__c` · `PRM_RecredDuePractitionersReportBatch` · `PractitionerLocationNetwork` / `PractitionerNetwork` (objects) · `TERM_NETWORK` / `TERM_GROUP` / `TERM_CONTRACT` / `TERM_AFFILIATION` / `endNetworkMembershipsOnly` (literals — requirements only) · `prmCheckClosedNetworkLogic` / `PRM_ClosedNetworkConfig__mdt` · `PRM_HCPFTriggerHelper.syncP2PEffectiveFromOldestActivePPL` / `PRM_FeatureConfigurationSettings__c.PRM_EnableP2PEffectiveFromAutoSync__c` · provider directory publication component · member PCP panel / capitation reassignment

### SOQL

Cohort resolution and reconciliation queries archived at **`requirements/SOQL/2026-08-19_SoftTermGroupWideCohort.md`** per `.cursor/rules/soql-queries-archive.mdc`.
