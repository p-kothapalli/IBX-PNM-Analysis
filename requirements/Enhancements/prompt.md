# Prompt — PNM Guided Flow → Apex Service Architecture Migration Doc + HTML Mind Map

> Re-usable prompt for any PNM guided flow (e.g. Term, QC Review, Vendor Audit, Practitioner Demographics, Adverse Action, etc.). Feeding this prompt + the name of the flow to any agent (or to a fresh chat with this codebase loaded) should produce **two synchronized artefacts** equivalent in depth and structure to the six docs already in `requirements/Enhancements/`:
>
> **Artefact 1 — Markdown migration doc:**
> - `PNM_Apex_Service_Architecture.md` (the generic framework — produced once)
> - `PNM_ParForm_RecordCreation_Apex_Service_Architecture.md` (Practitioner Participation Form — submit)
> - `PNM_PDA_ReviewUpdate_Apex_Service_Architecture.md` (Initial Cred PDA Review)
> - `PNM_OffCycle_Process_Apex_Service_Architecture.md` (Off Cycle submit)
> - `PNM_OffCycle_PDA_ReviewUpdate_Apex_Service_Architecture.md` (Off Cycle post-committee)
> - `PNM_Reinstate_Apex_Service_Architecture.md` (Reinstate — Practitioner / Loc / Vendor)
>
> **Artefact 2 — Interactive HTML mind map** (the stakeholder-facing visualization):
> - `PNM_Modernization_MindMap.html` (single self-contained file, FLOWS array drives every flow tab)
>
> The HTML uses the **same Why / How / Outcome / Replaces content** as the markdown's §6 service callouts, surfaced as expandable rows with detail cards. Producing a markdown doc without enriching the HTML is incomplete work — the HTML is the only artefact non-engineers actually open.
>
> The prompt is opinionated: it tells the agent exactly which sections to produce, which evidence to gather, which naming conventions to follow, which reusable services already exist after the previous migrations, and how to keep the markdown doc and the HTML mind map in lock-step. **Do not paraphrase or compress. Produce the full structural template every time, and update the HTML in the same change.**

---

## 0. Context — what the work is and why it exists

We are migrating a Salesforce Health Cloud / Provider Network Management (PNM) implementation for **Independence Blue Cross (IBX)** from heavyweight **OmniStudio Integration Procedures (IPs)** into a **scalable Apex Service Framework**. The framework follows a layered SOA pattern (Dispatcher → BaseService → Domain Service → Reactivator/Updater → Selector / Transformer / DML / Async) with automatic sync / async (Queueable / Batchable) delegation based on governor limits.

Each PNM guided flow today is one OmniScript that calls 1..N Integration Procedures. The IPs orchestrate 10–80+ elements: DataRaptor Posts / Extracts / Transforms / Turbos, Remote Actions into Apex utility classes, Conditional Blocks, Loop Blocks, Set Values, and Try/Catch wrappers. The OmniStudio scaffolding is **the bottleneck** — it blows governor limits at scale, costs many CPU-ms per row evaluation, and prevents code reuse across flows. Apex services preserve the OmniScript JSON contract while moving the orchestration into clean, testable, reusable Apex.

**Your job (per invocation of this prompt):** produce **two artefacts in lock-step** for one guided flow:

1. A markdown migration doc that follows the structural template in §3, mapping every IP element to its Apex replacement (REUSE / EXTEND / NEW / STANDARDISE), with the four-callout block (Why / How / Outcome / Replaces) under every §6 service heading per §3.A, and quantifying the reuse score against the running inventory in §5.
2. A new (or replaced) flow entry in the HTML mind map's `FLOWS` array per §7.2, with a fully-enriched `services` array whose `replaces` / `why` / `how` / `outcome` strings are byte-identical to the markdown §6 callouts.

---

## 1. Invocation — how to run this prompt

When the user asks you to "do the same research / migration plan for the **<Flow Name>** flow", you must:

1. **Confirm the flow name and the entry OmniScripts** (ask the user if unclear, but only one round of clarifying questions; otherwise discover via Glob — see §2.1).
2. **Run the research checklist in §2** (Discovery → IP audit → Records inventory → Variants → Existing Apex precedent).
3. **Produce the document using the structural template in §3** — every section, in order.
4. **Use the reusability inventory in §5** to mark each Apex replacement as REUSE / EXTEND / NEW / STANDARDISE.
5. **Save the output as `PNM_<FlowName>_Apex_Service_Architecture.md`** in `requirements/Enhancements/`.
6. **Cross-link** the new doc to every existing companion doc.
7. **Use the chunked-write technique in §7.1** to avoid the JSON-tool-call size limit (Write a placeholder, then `StrReplace` section-by-section).
8. **Add the Why / How / Outcome callouts** under every service heading in §6 of the markdown (mandatory — see §3.1 and §8 rule 11).
9. **Enrich the HTML mind map** at `requirements/Enhancements/PNM_Modernization_MindMap.html` for this flow — add the flow object to the `FLOWS` array (or replace the plain services list if the flow already exists), with the same `replaces` / `why` / `how` / `outcome` content as the markdown callouts. Follow the workflow in §7.2.
10. **Verify both artefacts together** — run the §10 validation checklist (which now covers both the markdown and the HTML).

---

## 2. Research Checklist — evidence-gathering before writing anything

> **Do this work first. Do not start writing the doc until every step below has been completed.** Cite the actual files you read. If a step returns nothing, say so explicitly in the doc.

### 2.1 Discovery (Glob)

For a flow named `<X>`, search for:

```
**/PRM*<X>*                              — every file with the name
**/omniScripts/PRM*<X>*                  — the OmniScript driver(s)
**/omniIntegrationProcedures/PRM*<X>*    — the IP container + orchestrator
**/vlocity_export/IntegrationProcedure/PRM_<X>*/PRM_<X>*_DataPack.json
**/vlocity_export/IntegrationProcedure/PRM_<X>*/PRM_<X>*_Element_*.json
**/classes/PRM_<X>*.cls                  — existing Apex (utils / batches / wrappers)
**/lwc/prm<X>*                           — related LWC
**/omniDataTransforms/PRM*<X>*           — DataRaptor bundles
```

Identify:
- The **entry OmniScripts** (often 1–4 per flow; English / Spanish / variants)
- The **container IPs** (`*Parent` or `*Container` — typically 3–5 elements: SetValues → TryCatch → IP Action → Response)
- The **orchestrator IPs** (the heavy ones — 10 to 80+ elements)
- Any **helper IPs** (validation, fetch, address-prep, Precisely-API wrapper)
- Any **existing Apex** that already partially implements the flow (Callable, Batch, Helper, Utils, AuraEnabled methods)

### 2.2 IP element audit (Read the DataPack + key element JSONs)

For **every** orchestrator IP in the flow:

1. Read `PRM_<X>_DataPack.json` and capture the **`OmniProcessElement` array** — that is the exact list of elements in order.
2. For each conditional block (`Type=Conditional Block`), read the element file and capture the **`executionConditionalFormula`** verbatim. Examples you have already seen:
   - `"%PDAOutCome% == \"NetworkQC\""`
   - `"%ChangeRequested% LIKE \"Specialty Change\" || %ChangeRequested% LIKE \"Role Change\""`
   - `"ISNOTBLANK(%RecordsToUpdate:PracticeLocationTable%) && %RecordsToUpdate:CaseType% = 'PDA Review and Update'"`
   - `"%RecordToUpsert:PracticeLocationCount% > 10"`
3. For each `DataRaptor Post Action` / `DataRaptor Turbo Action`, capture:
   - **`bundle`** name (this is the DataRaptor bundle that gets retired)
   - **`additionalInput`** keys (these tell you what data the bundle needs)
   - **`executionConditionalFormula`** (the gating condition)
4. For each `DataRaptor Extract Action`, capture the **bundle** (read-side) — these get folded into Apex selectors.
5. For each `DataRaptor Transform Action`, capture the **bundle** (pure transformation) — these get folded into Apex transformers.
6. For each `Remote Action`, capture:
   - **`remoteClass`** + **`remoteMethod`** (e.g. `PRM_OmniUtils.cloneBasisMultipleRole`)
   - **`additionalInput`** keys
7. For each `Loop Block`, note what list it iterates over.
8. For each `Set Values` step that does substantive shaping (not just renaming), note the key transformations.

> **Output of this step:** an ordered table — `# | Element name | Type | Bundle / RA | Cond | Purpose`. This becomes §1.3 of the doc.

### 2.3 Records inventory

By reading the DR bundles' `additionalInput` and field paths (or by inferring from the bundle name), build:

- **INSERT inventory** — one row per (SObject, source element, volume per submit, gating condition)
- **UPDATE inventory** — one row per (SObject, source element, when triggered, fields touched)
- **Variant axis** — the picklist(s) or numeric thresholds that fan out behaviour (e.g. `OffCycleRequestType` × `ChangeRequested` × volume)

The 9 SObjects you will see repeatedly in this codebase are:
- `Account` (PersonAccount practitioner or Vendor)
- `HealthcareFacility` (HCF)
- `Location` / Practice Location
- `HealthcarePractitionerFacility` (HCPF)
- `HealthcareFacilityNetwork` (HCFN)
- `HealthcareProviderTaxonomy` (HPT)
- `HealthcareProviderNpi` (HCPNPI)
- `Identifier__c`
- `Case`, `IndividualApplication` (CaseManager), `BoardCertification__c`, `PRM_InfoCodeAssignment__c`, `PRM_ProviderFeature__c`, `LocationNPIHistory`, `Address`, `ContentDocumentLink`, `ContentNote`

### 2.4 Existing Apex precedent

Check whether the flow already has **any** Apex implementation today:

- A `*Callable` class invoked from a Remote Action (the most common precedent — see `PRM_ReinstateCallable`)
- A `*Batch` or `*Batchable` (e.g. `PRM_ReinstateVendorAccountBatch`)
- A `*Utils` AuraEnabled selector for an LWC (e.g. `PRM_ReinstateUtils`)
- An LWC that drives the OmniScript
- A wrapper / DTO class

If precedent exists, you must:
- **Keep the existing Apex verbatim** in the migration plan (do not propose rewriting it)
- Treat it as **STANDARDISE** in the reusability matrix (not REUSE — because invocation changes)
- Specifically document the *invocation change* (e.g. "today called by `RA_CallBatch` Remote Action; tomorrow called directly by `PRM_<X>Service.processAsync()` — same `Database.executeBatch(...)` call, no behaviour change")

### 2.5 Variant axis cataloguing

Build a table cross-multiplying the variant picklists. Example from the Off Cycle docs:

| PDAOutCome | ChangeRequested | What runs |
|---|---|---|
| Approve | any | nothing in the IP — case status update via OS |
| RerouteToQM | any | Branch B (4 elt) — case + identifier + note |
| NetworkQC | Role Change | A01 + A11 + A12 + A13 sub-block |
| ... | ... | ... |

This table becomes §2.3 of the doc.

---

## 3. Structural template — produce these sections in this exact order

Use these headings verbatim. Every doc must have all 13 sections.

```
# PNM <Flow Name> — Apex Service Architecture
## IP Audit, Reusability Matrix & New Service Blueprint (<one-line scope>)

> Companion docs block — link to all five prior docs and the generic framework

---

## 0. TL;DR
   Side-by-side comparison table:
     Par Form  |  <closest prior flow>  |  THIS FLOW
   Rows: trigger, entry OS, entry IP, orchestrator IP, heaviest IP,
         variant axis, DML pattern, reusable framework code %,
         net-new services needed

---

## 1. Current State: Complete IP Chain Audit
   1.1  Full IP orchestration chain — ASCII tree diagram showing
        OmniScript → Container IP → Orchestrator IP → all elements,
        with element numbers, conditional formulas (raw), DR bundles,
        and Remote Action targets. This is the canonical reference.
   1.2  Element counts table — IP | Elements | Active Version | Type
   1.3  Per-element catalog — grouped by functional area (Case/Note,
        Fetch/Transform, Branch A, Branch B, ...) with columns:
        #  | Element | Type | Bundle / RA | Cond | Purpose

---

## 2. Records Created / Updated
   2.1  INSERT inventory — SObject | Source DR/RA | Volume | Notes
   2.2  UPDATE inventory — SObject | Source | When | Fields touched
   2.3  Variant axis — picklist × picklist cross-table

---

## 3. Target Apex Service Architecture
   3.1  Layered diagram — ASCII boxes for:
          OmniScripts (kept) / Thin-wrapper IPs (3-elt each)
          → CONTROLLER LAYER (ServiceDispatcher / BaseService)
          → ORCHESTRATION LAYER (NEW services for THIS flow)
          → SUPPORT LAYER (Selectors, Transformers)
          → CROSS-CUTTING (DMLUtil, CollectionUtil, GovernorUtil,
            ErrorLogger, TransactionContext, AsyncJobBase)
          → TX1 / TX2 split
          → Database / Platform
   3.2  Transaction Boundary table — Phase | TX | Scope | Rationale
   3.3  OmniScript / IP Dispatcher wiring — show how the orchestrator
        IPs collapse to "SetValues → ServiceInvoker → Response"
   (3.4 only when there is an existing Apex precedent to consolidate —
        document the standardisation)

---

## 4. Reusability Matrix
   4.1  Framework / Cross-cutting — table of REUSE rows
   4.2  Selectors — REUSE / NEW per selector
   4.3  Transformers — REUSE / NEW per transformer
   4.4  External integration (if any — Precisely, NPDB, etc.)
   4.5  Domain / Orchestration services — REUSE / EXTEND / NEW per service
   4.6  Reuse Score table:
            Bucket | Reused | Extended | New | Standardise | Total
        with % reused computed across class count.

---

## 5. Element-by-Element Migration Map
   Per IP, per group, a table:
     # | IP element | Apex replacement | Disposition
   This is the doc's longest section. Every IP element appears here.

---

## 6. Service Code — key signatures
   Apex skeletons (~50–100 lines each) for:
     6.1  The top-level orchestrator service (the one registered in the dispatcher)
     6.2  The heaviest sub-service (e.g. the Network/HCFN one)
     6.3  Any EXTEND of an existing service (show only the new method)
     6.4  The Queueable / Batchable async wrapper
     6.5  Any service that has unique branching logic
   Code uses real SObject names from the IBX schema (HealthcareFacility,
   HealthcareFacilityNetwork, HealthcarePractitionerFacility, etc.) and
   real field names from the bundles. NEVER hallucinate fields.

   IMPORTANT — every §6 sub-section MUST include a four-callout block
   immediately under the heading, BEFORE the code block. This is the
   stakeholder-facing explanation pattern used across all 6 prior docs.
   The four callouts are:
     > **Why we need it** — the production pain this service eliminates,
     >   referencing the actual IP element / DR / Remote Action by name.
     >
     > **How it helps** — the technical mechanism: what pattern, what
     >   data flow, what shared utilities it composes.
     >
     > **Outcome** — the measurable result. Numbers preferred (X→Y),
     >   behaviour changes accepted.
     >
     > **Replaces** — explicit list of legacy IPs / DRs / RAs retired
     >   (this maps 1-to-1 to the `replaces` field in the HTML mind map).
   See §3.A below for the exact prose pattern, and §7.2 for how the same
   four fields are duplicated into the HTML services array.

---

## 7. Sequence Diagram (target state)
   ASCII swim-lane sequence for the worst-case / most-interesting path.

---

## 8. Governor / Performance Comparison
   Table: Today | After (TX1) | After (TX2) for SOQL, DML, DML rows,
                                                CPU, Heap, external callouts.

---

## 9. Migration Plan
   9.1  Sequencing — number this migration in the global order
        (Par Form → PDA Review → Off Cycle Submit → Off Cycle PDA →
         Reinstate → THIS FLOW → ...)
   9.2  Components to retire — explicit lists per type (IPs, DRs,
        Remote Action methods, existing Apex if any)
   9.3  Test Strategy — Layer | Tests
   9.4  Feature Flag Rollout — PRM_FeatureConfig__mdt entries with
        defaults

---

## 10. Risks & Mitigations
   Table — Risk | Mitigation. At minimum cover:
     • Shared util coordination with prior migrations
     • Most-complex transformation correctness (test-first + dual-write)
     • Async-before-downstream race conditions
     • Feature-flag isolation
     • Existing Apex preservation (if any)
     • OmniScript contract preservation
     • Picklist semantics (multi-select LIKE vs ==)

---

## 11. Acceptance Criteria
   Numbered list of 7–10 hard, measurable criteria. Always include:
     • All IPs shrink to 3 elements each
     • Bit-identical row set under dual-write
     • Sync request < 1 s for worst case
     • Async TX2 < 60 s
     • Zero changes to OmniScript JSON
     • Coverage ≥ 90% / 80%
     • Feature flag cleanly reverts to legacy

---

## 12. Net new vs reused — one final view
   Category-by-category LoC estimate.

---

## 13. Cross-references
   Bulleted links to every companion doc.
```

---

### 3.A The Why / How / Outcome / Replaces callout pattern (mandatory under every §6 heading)

Every Apex service shown in §6 is a stakeholder-readable artefact, not just code. Stakeholders (PNM SMEs, leadership, leads of adjacent feature teams) read the doc to understand *why* the rewrite is worth doing — they do not read Apex. The four-callout block under every §6 heading is the bridge.

Use this exact prose pattern (Markdown blockquote, four `>` paragraphs, bolded labels, em-dash separator). All four bullets are mandatory; do not omit any. Length per bullet: 1–4 sentences.

```
### 6.X `PRM_<ServiceName>` (one-line role)

> **Why we need it** — <Production pain.> Reference the specific IP
> element, DR bundle, Remote Action class, or known production
> incident class. Be concrete: "the 38-element orchestrator IP",
> "the 4 Remote Action round-trips in HFN reshape", "the IP-level
> Conditional Block that re-reads screen state on every step".
>
> **How it helps** — <Technical mechanism.> Name the pattern
> (Template Method / Registry-Dispatcher / Queueable / Partial-success
> DML), the shared utilities the service composes (PRM_DMLUtil,
> PRM_CollectionUtil, etc.), and the key data flow (single bulk read
> via selector, in-memory transform, partial-success write).
>
> **Outcome** — <Measurable result.> Prefer numbers: "40 IP elements
> → ~150 lines", "Sync TX1 < 700 ms", "4 Remote Action round-trips → 0",
> "DML rows: 22 → 5". Behaviour changes acceptable when no number
> is available: "stuck-state cases eliminated", "race-condition
> duplicates eliminated via upsert semantics".
>
> **Replaces** — <Comma-separated list of legacy components retired.>
> Use the verbatim names from §1.3 (DR bundle names, IP names,
> Remote Action method paths). This list MUST equal the value of
> the `replaces` field in the HTML services entry for this service
> (see §7.2).

```apex
public with sharing class PRM_<ServiceName> extends PRM_BaseService {
    ... 50-100 lines of skeleton ...
}
```
```

Style notes:

- The `Replaces` bullet is the **bridge to the HTML**. The string used here MUST be the same string used in the HTML services array entry's `replaces` field. Copy-paste consistency is mandatory; treat any drift as a bug.
- For services marked **REUSE** in §4.5 that you still want to enumerate in the HTML, the callouts can be terser ("Reused as-is from <prior flow>") but still include all four. The HTML uses these to render the "Reused" rows with detail cards just like NEW rows.
- For services marked **STANDARDISE** (existing Apex kept verbatim), the `Why we need it` bullet must say *why we are NOT rewriting it* (production-hardened, ~N LoC, zero regression risk) and the `Outcome` bullet should say "Zero regression risk; only the dispatch hop changes."

---

## 4. Naming conventions — use these verbatim

### 4.1 Apex class naming

- **Top-level orchestrator service**: `PRM_<FlowName>Service` (e.g. `PRM_OffCycleSubmitService`, `PRM_ReinstatePractitionerService`)
- **Sub-services**: `PRM_<FlowName><Domain>Service` or `<Verb>or` (e.g. `PRM_OffCycleAddressService`, `PRM_BoardCertReactivator`)
- **Selectors**: `PRM_<SObject>Selector` for generic, `PRM_<FlowName>Selector` for flow-specific bulk façades
- **Transformers**: `PRM_<FlowName><Subject>Transformer` (e.g. `PRM_OffCycleAddressTransformer`, `PRM_OffCyclePDAHFNTransformer`)
- **Async jobs**: `PRM_<FlowName>AsyncJob` (Queueable) or `PRM_<FlowName>Batch` (Batchable)
- **DTOs**: `<FlowName>DTO` or `<FlowName>Result`
- **Extensions**: name the extending class differently from the parent (`PRM_OffCycleAddressService extends PRM_AddressService`, not `PRM_AddressServiceOffCycle`)

### 4.2 Service names (registered in `PRM_ServiceDispatcher`)

`<FlowName>` in PascalCase, no `PRM_` prefix in the registry key, e.g.:
- `"OffCycleSubmit"` → `PRM_OffCycleSubmitService`
- `"OffCyclePDAReview"` → `PRM_OffCyclePDAReviewService`
- `"ReinstatePractitioner"` → `PRM_ReinstatePractitionerService`

### 4.3 OmniStudio dispatcher wiring (always identical)

Every migrated orchestrator IP shrinks to:

```
SetValues → IP Action (PRM_ServiceInvoker) → ResponseAction
              serviceName = "<RegistryKey>"
              payload     = %ContextPayload%
```

`PRM_ServiceInvoker` is the existing generic IP that bridges into `PRM_ServiceDispatcher.invokeMethod('<RegistryKey>', input, output, options)`.

### 4.4 Feature flags

`PRM_FeatureConfig__mdt.<FlowName>_UseApexService` (Boolean, default `false`) — controls the cut-over per flow.
`PRM_FeatureConfig__mdt.<FlowName>_AsyncThresholdRows` (Integer) — TX1/TX2 split threshold.

When a flow has multiple scopes (e.g. Reinstate has Practitioner / PracticeLocation / Vendor), use **one flag per scope** so each cuts over independently.

### 4.5 Platform events

- `PRM_AsyncComplete__e` (already exists) — fired by every Queueable / Batchable on completion. Fields: `JobName__c`, `ContextId__c`, `Success__c`, `Payload__c`.
- `PRM_ExceptionLog__c` (already exists) — written via `PRM_ErrorLogger.logException(...)`.

---

## 5. Reusability inventory — what already exists after each prior migration

This is the **running tally** of available services. Use it to mark each Apex replacement.

### 5.1 Framework / Cross-cutting (available from day 1)

| Class | Purpose |
|---|---|
| `PRM_ServiceDispatcher` | Registry: serviceName → BaseService instance |
| `PRM_BaseService` | Template Method base — `processSync()`, `processAsync()`, auto sync/async delegate |
| `PRM_ServiceRequest`, `PRM_ServiceResponse` | DTO wrappers |
| `PRM_TransactionContext` | Per-request context for logging / correlation |
| `PRM_DMLUtil` | Partial-success DML (`allOrNone=false`) for insert / update / upsert |
| `PRM_CollectionUtil` | LA-merge / filter / dedup / indexBy / flatten equivalents |
| `PRM_GovernorUtil` | `shouldDelegateAsync(rowCount)` decision |
| `PRM_ErrorLogger` | Writes `PRM_ExceptionLog__c` + correlates with `PRM_AsyncComplete__e` |
| `PRM_AsyncJobBase` | Queueable parent — provides try/catch + AsyncComplete publish |
| `PRM_FeatureConfig` | Reads `PRM_FeatureConfig__mdt` |
| `PRM_RecordTypeUtil` | RecordType ID cache |
| `PRM_TestDataFactory` | Test fixture builder |

### 5.2 After Par Form migration

| Class | Purpose |
|---|---|
| `PRM_CaseService` | Case + IndividualApplication create / close / link |
| `PRM_NoteService` | ContentNote creation, getCaseNotes |
| `PRM_AddressService` | Location / HCF / HCPF / Address bulk insert orchestration |
| `PRM_IdentifierService` | Identifier__c + ContentDocumentLink insert |
| `PRM_AccountUpsertHelper` | PersonAccount + Vendor Account upsert |
| `PRM_PersonEducationService` | PersonEducation bulk insert |
| `PRM_PreciselyAdapter` | Precisely USPS callout (batched validate) |
| `PRM_PreciselyResponseMapper` | Precisely response decoder |
| `PRM_AccountSelector`, `PRM_HCFSelector`, `PRM_HCPFSelector`, `PRM_IdentifierSelector` | Standard selectors |
| `PRM_ParFormDataTransformer` | Par Form address shaping |

### 5.3 After PDA Review (Initial Cred) migration

| Class | Purpose |
|---|---|
| `PRM_PDAOrchestratorService` | Top-level PDA Review orchestrator |
| `PRM_AccountUpdater` | PersonAccount update — attestation, taxId, demographics |
| `PRM_TaxonomyService` | HealthcareProviderTaxonomy create / update / effective-date |
| `PRM_HCFNetworkSelector` | Selector for HCFN + payer network + info codes |
| `PRM_NetworkCloneUtil` | Shared cloneBasisMultipleRole + cloneHCFNRecords (moved out of PRM_OmniUtils) |

### 5.4 After Off Cycle Submit migration

| Class | Purpose |
|---|---|
| `PRM_OffCycleSubmitService` | Off Cycle submit orchestrator |
| `PRM_OffCycleCaseService` (extends `PRM_CaseService`) | Off Cycle case factories |
| `PRM_OffCycleIdentifierService` (extends `PRM_IdentifierService`) | Off Cycle identifier (incl. FormProcess="Off-Cycle Request") |
| `PRM_OffCycleContactService` | Contact-side Account upsert (changed contacts only) |
| `PRM_OffCycleGroupService` | Vendor Account + Group Identifier + Group HCPNPI |
| `PRM_OffCycleAddressService` (extends `PRM_AddressService`) | Off Cycle address + existing-facility NPI update |
| `PRM_OffCycleNetworkService` | Role-explosion + HCFN insert + taxonomy create |
| `PRM_OffCycleAffiliationService` | Practitioner ↔ Vendor HCPF link |
| `PRM_OffCycleExpediteService` (extends `PRM_AccountUpdater`) | Expedited Account flag |
| `PRM_OffCycleFormFetchService` | Bulk form-load |
| `PRM_OffCycleAddressValidationService` | Precisely wrapper |
| `PRM_OffCycleAsyncJob` (extends `PRM_AsyncJobBase`) | TX2 Queueable |
| `PRM_LocationNPIHistorySelector` | LocationNPIHistory selector |
| `PRM_OffCycleFormSelector` | Bulk form fetch façade |
| `PRM_OffCycleAddressTransformer`, `PRM_OffCycleNetworkTransformer`, `PRM_OffCyclePFAATransformer`, `PRM_OffCycleContactDeltaTransformer` | Off Cycle transformers |

### 5.5 After Off Cycle PDA Review migration

| Class | Purpose |
|---|---|
| `PRM_OffCyclePDAReviewService` | Off Cycle PDA orchestrator (switch on PDAOutCome) |
| `PRM_OffCycleApproveService`, `PRM_OffCycleRerouteToQMService`, `PRM_OffCycleNetMgmtQCService` | PDA branch services |
| `PRM_OffCycleSendToPDAService`, `PRM_OffCycleNetworkQCService` | Stage 1 / Stage 3 services |
| `PRM_OffCyclePDAHFNTransformer` | HCFN reshape (demerge + info-code merge + reshape + detect-unused) |
| `PRM_LocationNPIHistoryService` | NPI history close-prior + open-new |
| `PRM_AttestationDateUpdater` | Attestation-date touch |
| `PRM_OffCyclePDAAsyncJob` | TX2 Queueable for PDA path |
| `PRM_TaxonomyService.committeeApprove(...)` | Extension method — effective-date NULL, Pending=FALSE |
| `PRM_OffCycleNetworkService.processCommitteeApprovedNetworks(...)` | Extension method — Pending=FALSE + deactivate-unused |

### 5.6 After Reinstate migration

| Class | Purpose |
|---|---|
| `PRM_ReinstatePractitionerService`, `PRM_ReinstatePracticeLocationService`, `PRM_ReinstateVendorAccountService` | Per-scope orchestrators |
| `PRM_ReinstateRowPartitioner` | Generic bucket-sort (ReinstateAs × Update) |
| `PRM_ReinstateTransformer` | Reinstate-side transforms |
| `PRM_ReinstateSelector` | Bulk read façade |
| `PRM_PractitionerAccountReactivator`, `PRM_HCFReactivator`, `PRM_HCPFReactivator`, `PRM_HCFNReactivator`, `PRM_BoardCertReactivator`, `PRM_InfoCodeReactivator`, `PRM_ProviderFeatureReactivator` | Single-SObject reactivators |
| `PRM_TaxonomyReactivator` (extends `PRM_TaxonomyService`) | Taxonomy reinstate method |
| `PRM_IdentifierReactivator` (extends `PRM_OffCycleIdentifierService`) | Identifier reinstate method |
| `PRM_ReinstateVendorAccountBatch` + Helper (already exists in org — kept verbatim) | Vendor batch for >10 locations |
| `PRM_ReinstateUtils` (already exists in org — kept verbatim) | AuraEnabled selector for LWC |
| `PRM_CaseDataMgrService.stampReinstateFlags(...)` | Reinstate flag stamp (added to existing service) |

### 5.7 SObject + field cheat-sheet

| Concept | SObject | Active flag | Effective date | Other key fields |
|---|---|---|---|---|
| Practitioner | `Account` (PersonAccount) | `IsActive`, `PRM_Active__c` | `EffectiveTo`, `PRM_ReinstateDate__c` | `PRM_AttestationDate__c`, `PRM_Expedited__c` |
| Vendor / Group | `Account` (Business) | `IsActive` | `EffectiveTo` | RecordType = "Medical Service Vendor" |
| Healthcare Facility | `HealthcareFacility` | `PRM_Active__c` | `EffectiveDate__c`, `EffectiveTo` | `NPI`, `PRM_Pending__c` |
| Location | `Location` | `IsActive` | `EffectiveTo` | `Address` (inline) |
| Practitioner-Facility | `HealthcarePractitionerFacility` (HCPF) | `IsActive` | `EffectiveTo` | RecordType = `PRM_PractitionerLocationAffiliation` |
| Network Affiliation | `HealthcareFacilityNetwork` (HCFN) | `IsActive` | `EffectiveTo` | `PRM_Pending__c`, `NetworkId__c`, `BasisOfPractice__c` (role) |
| Provider Taxonomy | `HealthcareProviderTaxonomy` (HPT) | `IsActive` | `EffectiveTo`, `StartDate` | `TaxonomyCode`, `IsPrimary`, `PRM_BasisOfPractice__c` |
| Provider NPI | `HealthcareProviderNpi` (HCPNPI) | `IsActive` | — | `NPI` |
| Identifier | `Identifier__c` | `IsActive`, `PRM_Active__c` | `EffectiveTo` | `Type__c`, `Value__c`, `FormProcess__c` |
| Board Cert | `BoardCertification__c` | `PRM_Active__c` | `EffectiveTo` | `BoardId__c`, `Specialty__c` |
| Info Code | `PRM_InfoCodeAssignment__c` | `PRM_Active__c` | `EffectiveDate__c`, `EffectiveTo` | `InfoCode__c` |
| Provider Feature | `PRM_ProviderFeature__c` | `IsActive` | `EffectiveTo` | (assistive aids / capabilities) |
| Location NPI period | `LocationNPIHistory` | — | `StartDate__c`, `EndDate__c` | one row per period |
| Case Manager | `IndividualApplication` | — | — | RecordType per flow; many `CaseDataManager*` flag fields |

### 5.8 Remote Action methods seen across the codebase

These all get **retired** as each flow migrates. Move the logic into shared utilities:

| Today | Target Apex |
|---|---|
| `PRM_OmniUtils.createNoteMulti` | `PRM_NoteService.createCaseNote` |
| `PRM_OmniUtils.cloneBasisMultipleRole` | `PRM_NetworkCloneUtil.demergeByRole` |
| `PRM_OmniUtils.cloneHCFNRecords` | `PRM_NetworkCloneUtil.cloneNetworkRows` |
| `PRM_OmniUtils.expandInfoCodes` | `PRM_OffCyclePDAHFNTransformer.expandInfoCodes` |
| `PRM_OmniUtils.logTryCatchException` | `PRM_ErrorLogger.logException` |
| `PRM_OmniUtils.getContentNote` | `PRM_NoteService.getCaseNotes` |
| `PRM_FetchOffCycleCredUtility.CreateHealthCareProvTaxonomy` | `PRM_OffCycleNetworkService.createTaxonomies` |
| `PRM_ReinstateCallable.ReinstateVendorAccountBatch` | direct `Database.executeBatch(new PRM_ReinstateVendorAccountBatch(...), 5)` |

If a Remote Action target is **shared by another in-flight migration**, keep it for now and add it to the "Risks" section of both docs as a coordination point.

---

## 6. Transaction Boundary Heuristics

Use these heuristics to decide TX1 vs TX2 per flow:

| Heuristic | TX1 (sync) | TX2 (async) |
|---|---|---|
| User must see a CaseId / IDs to continue navigation? | Yes — keep sync | n/a |
| Worst-case row count > 75? | n/a | Yes — Queueable |
| Worst-case row count > 200? | n/a | Yes — Batchable (or Queueable that re-enqueues) |
| Involves external callout (Precisely)? | If 1 batched call < 30s | If looped per-row → batch |
| Touches fewer than 10 rows total? | Yes — always sync | n/a |
| Has a per-row Yes/No flag with hundreds of rows? | n/a | Yes — partition in TX1, write in TX2 |
| Existing Apex precedent already uses a Batchable? | n/a | Yes — keep the Batchable verbatim |

Default threshold: `PRM_GovernorUtil.shouldDelegateAsync(estimatedRowCount > 75)`. Override per flow via `PRM_FeatureConfig__mdt.<FlowName>_AsyncThresholdRows`.

---

## 7. Authoring technique — keep both the markdown doc AND the HTML mind map in sync

Every flow migration produces **two artefacts** that must stay in lock-step: the markdown architecture doc (`PNM_<FlowName>_Apex_Service_Architecture.md`) and the corresponding flow entry inside the HTML mind map (`PNM_Modernization_MindMap.html`). The Why / How / Outcome / Replaces content appears in both — once as Markdown blockquotes under §6 of the doc, once as JSON fields on each service entry in the HTML's `FLOWS` array.

### 7.1 Markdown chunked writes (avoiding tool-size limits)

The Write tool fails with `Expected ',' or '}' after property value in JSON` when a single `contents` payload is too large. Use this proven 4-step pattern:

1. **Create a placeholder** with `Write`:
   ```
   path: requirements/Enhancements/PNM_<FlowName>_Apex_Service_Architecture.md
   contents: "# PNM <Flow Name> — Apex Service Architecture\n\n(placeholder)\n"
   ```
2. **First StrReplace** — swap the placeholder for the front matter (Companion docs block + TL;DR). End the new_string with a section delimiter `---` line.
3. **Subsequent StrReplaces** — for each new section, replace the trailing `---` plus an anchor line of the previous section with the new section's full content plus a new trailing `---`. This guarantees the `old_string` is unique each time.
4. **Verify** with `wc -l` at the end.

Each StrReplace should add roughly **one major section** (200–300 lines). Six StrReplaces is the sweet spot — one per major section grouping:
- Sections 0–1 (TL;DR + IP Audit)
- Section 2 (Records inventory)
- Section 3 (Architecture)
- Sections 4 (Reusability) + 5 (Migration map)
- Section 6 (Service code, **including the §3.A four-callout block under every heading**)
- Sections 7–13 (Sequence, governor, migration plan, risks, acceptance, net-new, cross-refs)

### 7.2 HTML mind map enrichment (mandatory for every new flow)

The HTML mind map at `requirements/Enhancements/PNM_Modernization_MindMap.html` has a top-level `FLOWS = [ ... ]` array (currently 5 entries; one per migrated flow). Each new flow you migrate must add (or replace) one entry there. The renderer is already wired to display every service as either a chip OR an expandable row with detail cards — the choice is data-driven: if a service entry has a `why` field, it renders as an expandable row; otherwise it falls back to a chip. **Always provide `why`** so the visualization is uniformly rich.

#### 7.2.1 The flow-entry shape

```javascript
{
  id: '<flow-id-kebab>',                          // e.g. 'practitioner-term'
  name: '<Display Name>',                          // e.g. 'Practitioner Term'
  short: '<Tab label>',                            // e.g. 'Term'
  icon: '<emoji>',                                 // single character
  tagline: '<one-sentence scope>',
  reuseScore: { label: '<X% reuse>', tone: 'high|highest|mixed' },
  docLines: <wc -l of the markdown doc>,
  docFile: 'PNM_<FlowName>_Apex_Service_Architecture.md',
  before: { 'Integration Procedures': '...', 'IP Elements': '...', /* 5-6 rows */ },
  after:  { 'Services': '...', 'TX1 (sync)': '...', /* 5-6 rows */ },
  perf:   [ { label: 'SOQL', value: 'X → Y' }, /* 4 rows */ ],
  tx:     { tx1: { label, title, body }, tx2: { label, title, body } },
  note:   '<HTML-allowed callout under the perf strip>',
  services: [ /* see 7.2.2 */ ],
  architecture: { current: [...], target: [...], summary: { currentLabel, targetLabel } },
  highlights: [ /* 4-5 hero entries for the tab card */ ],
}
```

Use any prior flow as a starting template (Off Cycle Submit / OffCycle PDA / Reinstate are the most current).

#### 7.2.2 The enriched `services` array shape (REQUIRED for every service)

Each service entry must be a JSON object with these fields:

```javascript
{ name: 'PRM_<ServiceName>',
  kind: 'reused' | 'extended' | 'new' | 'standardise',
  note: '<short tag, e.g. "Top-level orchestrator">',
  replaces: '<comma-separated legacy components retired — must equal the markdown §6 Replaces bullet verbatim>',
  why:     '<same content as the markdown Why we need it bullet, single string>',
  how:     '<same content as the markdown How it helps bullet, single string>',
  outcome: '<same content as the markdown Outcome bullet, single string>' },
```

Rules:

1. **Copy-paste from the markdown.** The four strings (`replaces`, `why`, `how`, `outcome`) MUST equal the four callout bullets under the corresponding §6 heading. Drift between MD and HTML is a defect.
2. **Cover every class in §4 of the markdown.** The `services` array length should equal `reused + extended + new + standardise` from the §4.6 reuse-score table. List every framework primitive, every selector, every transformer, every external integration, every domain service. Stakeholders need to see the full inventory.
3. **Order: reused → extended → new → standardise.** Within each kind, group by purpose (framework first, then selectors, then transformers, then domain services).
4. **Use Unicode escapes for typographic punctuation** inside string literals — `\u2019` for `'`, `\u2014` for em-dash. JavaScript single-quoted strings inside the HTML choke on raw curly quotes.
5. **For REUSED entries**, the `why` should explain why we are reusing (not re-writing) — usually "without reusing X, every flow re-implements Y".
6. **For STANDARDISE entries**, the `why` must say "this is already production-hardened Apex; rewriting would be high-risk for zero benefit". The `outcome` must be "Zero regression risk; only the dispatch hop changes" or equivalent.

#### 7.2.3 The placeholder + StrReplace pattern (avoiding StrReplace size limits)

Replacing the entire `services` array in one StrReplace can exceed the tool size budget for flows with 30+ services. Use the same chunking trick as for markdown:

1. **First StrReplace** — replace the existing plain `services: [ ... ]` block (or the missing flow block) with a placeholder:
   ```javascript
   services: [
     /* <FLOW>_SERVICES_PLACEHOLDER */
   ],
   ```
2. **Second StrReplace** — fill in the REUSED chunk by replacing `/* <FLOW>_SERVICES_PLACEHOLDER */\n    ],` with the full reused-services list followed by the closing `],` bracket on its own line.
3. **Third StrReplace** — append the EXTENDED + NEW + STANDARDISE chunk by replacing the **last reused entry's closing brace + `\n    ],\n    architecture: {`** with the same line + the new entries + a fresh closing `],\n    architecture: {`. Use the last reused entry as the unique anchor.
4. **Verify** by extracting the FLOWS array and counting enriched services per flow (see §7.2.4).

This 3-StrReplace pattern lands a fully enriched 30+ service array reliably. A single-shot StrReplace works for ≤20 services.

#### 7.2.4 Verification — Node.js FLOWS-array parse + service count

After every HTML update, run the following Node.js verification (works because the renderer code is browser-only but the FLOWS data is plain literal JSON-in-JS):

```bash
node -e "
const fs = require('fs');
const src = fs.readFileSync('requirements/Enhancements/PNM_Modernization_MindMap.html','utf8');
const startIdx = src.indexOf('const FLOWS = [');
let i = startIdx + 'const FLOWS = ['.length;
let depth = 1, inStr = false, strCh = null, escaped = false, inLineComment = false;
while (i < src.length && depth > 0) {
  const c = src[i];
  if (c === '\n') { inLineComment = false; i++; continue; }
  if (inLineComment) { i++; continue; }
  if (inStr) {
    if (escaped) { escaped = false; }
    else if (c === '\\\\') { escaped = true; }
    else if (c === strCh) { inStr = false; strCh = null; }
    i++; continue;
  }
  if (c === '/' && src[i+1] === '/') { inLineComment = true; i += 2; continue; }
  if (c === \"'\" || c === '\"' || c === '\`') { inStr = true; strCh = c; i++; continue; }
  if (c === '[') depth++;
  else if (c === ']') depth--;
  i++;
}
const block = src.slice(startIdx, i+1).replace('const FLOWS', 'globalThis.FLOWS');
eval(block);
for (const f of FLOWS) {
  const total = (f.services||[]).length;
  const why  = (f.services||[]).filter(s=>s.why).length;
  console.log(f.id.padEnd(22), 'svcs:', String(total).padStart(3), 'enriched:', String(why).padStart(3));
}
"
```

The expected output: every flow shows `svcs:N enriched:N` where N matches the §4.6 total. Any flow showing `enriched: 0` for a migrated flow is a defect — the services array is missing the `why` field.

#### 7.2.5 What you do NOT need to touch in the HTML

- The CSS / rendering code — already handles both chip-style fallback and the expandable-row + 4-card detail panel.
- The wiring functions (`wireServiceToggle()`, `wireLayerToggle()`) — already global, picks up new entries automatically.
- The Core Framework section (`CORE.layers`) — only changes when you add a new framework primitive; flow migrations do not touch it.

---

## 8. Style rules — keep every doc consistent

1. **Use real names**, never placeholders. If you don't know a field name, read the bundle XML or the SObject metadata first.
2. **Element conditions are verbatim** — copy the `executionConditionalFormula` exactly, including `LIKE`, `==`, and the multi-pipe ORs.
3. **Tables over prose** for every catalog. Prose is reserved for §0 TL;DR, §3.1 introduction, §9.1 sequencing, and §10 risks.
4. **ASCII diagrams over Mermaid** — every diagram in the existing six docs is ASCII because GitHub-flavoured Markdown renderers reliably display monospaced ASCII. Width target: 80–110 columns.
5. **Reuse score is a hard number**, not "high / medium / low". Count classes; show the ratio.
6. **Acceptance criteria are measurable** — every criterion has a number (rows, ms, % coverage, count of IPs that shrink).
7. **Cross-reference every prior doc** in §13 — these docs are a chain; each one builds on the previous.
8. **Code blocks** in §6 use real Apex syntax (`public with sharing class`, `@TestVisible`, `Database.allOrNone=false`) and reference the actual SObject API names in §5.7.
9. **Migration order** is sticky — the global sequence is **Par Form → PDA Review → Off Cycle Submit → Off Cycle PDA → Reinstate → <new flows>**. Every new doc places itself in this order and explicitly notes what it can/can't reuse.
10. **Every §6 service heading carries the four-callout block** (Why we need it / How it helps / Outcome / Replaces) per §3.A. No exceptions, including REUSED and STANDARDISE entries.
11. **Markdown §6 callouts and HTML services-array fields are 1-to-1.** The exact same string appears in both places. If one is updated, the other must be updated in the same change.
12. **No emojis** anywhere.

---

## 9. Anti-patterns — do not do these

| Anti-pattern | Why it's wrong |
|---|---|
| Inventing service names or methods that don't exist in §5 | Other docs reference these classes — invented names break the chain |
| Marking everything as NEW | Defeats the purpose; check §5 first |
| Skipping conditional formulas | The branching is the whole story; you must show every condition verbatim |
| Compressing tables into prose | Lowers signal-to-noise and breaks cross-doc consistency |
| Using `==` for multi-select picklists | They use `LIKE` because the values are pipe-delimited; mirror it in Apex with `Set<String>` membership checks |
| Hallucinating bundle names | Always read the element JSON's `additionalInput.bundle` |
| Recommending a rewrite of existing Apex (e.g. `PRM_ReinstateVendorAccountBatch`) | Always preserve existing Apex verbatim — only the *invocation* changes |
| Writing the whole doc in one Write call | Will fail with the JSON size error; use chunked StrReplace per §7 |
| Skipping the OmniScript JSON-contract preservation criterion | Every flow migration must keep the OS contract identical; that's the whole reason this works |

---

## 10. Validation checklist — run before declaring the doc done

### 10.1 Markdown doc

- [ ] §1.1 ASCII chain diagram includes every element from every orchestrator IP in the flow.
- [ ] §1.3 catalog has one row per element, with verbatim conditions and bundle names.
- [ ] §2.1 + §2.2 inventories together cover every DML in the flow (no SObject from §1.3 is missing).
- [ ] §3.1 layered diagram lists exactly which support-layer classes are REUSE vs NEW.
- [ ] §4.6 reuse score table totals match the sum of classes mentioned in §4.1–§4.5.
- [ ] §5 has a row for every element in §1.3.
- [ ] **§6 every service heading carries the four-callout block** (Why we need it / How it helps / Outcome / Replaces) per §3.A. Zero headings missing any callout.
- [ ] §6 service skeletons reference SObject + field names from §5.7.
- [ ] §9.2 retirement list names every IP and every DR bundle that appears in §1.3.
- [ ] §11 has at least one criterion per major DML category (sync, async, OmniScript contract, coverage, feature flag).
- [ ] §13 links to every prior companion doc.
- [ ] Total line count is in the 800–1,300 range. Significantly shorter means missed depth; significantly longer means redundancy.
- [ ] The doc passes a final `wc -l` and `rg "TODO|TBD|XXX|FIXME"` check (zero hits).

### 10.2 HTML mind map

- [ ] The new flow appears in the `FLOWS` array of `PNM_Modernization_MindMap.html`.
- [ ] The flow's `services` array length equals the §4.6 reuse-score total (reused + extended + new + standardise).
- [ ] **Every service entry has all four enrichment fields**: `replaces`, `why`, `how`, `outcome`. Run the §7.2.4 Node.js verification — `enriched: N` must equal `svcs: N` for the new flow.
- [ ] Each `replaces` / `why` / `how` / `outcome` string is byte-identical to the matching markdown §6 callout bullet.
- [ ] Services are ordered: reused → extended → new → standardise (within each kind, framework → selectors → transformers → domain).
- [ ] Typographic punctuation inside string literals uses Unicode escapes (`\u2019`, `\u2014`) — no raw curly quotes that would break JS parsing.
- [ ] `architecture.current` / `architecture.target` lists the full layer stack (OmniScript → Container IPs → Orchestrator → Helpers → DRs / RAs in current; OmniScript → Thin IPs → Dispatcher → Orchestrator + Sub-services → Reused/Extended → Async in target).
- [ ] `before` / `after` / `perf` / `tx` / `note` / `highlights` are all populated (no defaults or placeholders).
- [ ] `docLines` matches `wc -l` of the markdown doc.
- [ ] HTML has no linter errors (`ReadLints` returns clean).

---

## 11. Example invocation

> User: "Now do a similar research and migration plan for the **Practitioner Termination** guided flow. Save it to `requirements/Enhancements/`."

Expected agent behaviour:

1. **Discovery** (Glob):
   - `**/PRM*Term*` → finds OS, IPs, DRs, any existing Apex
   - `**/PRM*Termination*`
   - `**/omniScripts/PRM*Term*`
2. **Confirm the entry OmniScripts and orchestrator IP names** with the user only if ambiguous.
3. **Read** the DataPack JSON for each orchestrator IP, and the key conditional + DR Post element JSONs.
4. **Build** the element catalog, INSERT/UPDATE inventories, and variant axis.
5. **Check** for existing Apex (Callable, Batch, Utils) — note if any of the Off Cycle Term path is already handled via Off Cycle Submit's `OffCycleRequestType = "Term"` branch.
6. **Write** placeholder file, then chunked StrReplace per §7.1.
7. **Author the §6 service code section with the four-callout block** under every heading per §3.A.
8. **Enrich the HTML mind map** at `requirements/Enhancements/PNM_Modernization_MindMap.html` per §7.2 — add the new flow object to the `FLOWS` array with a fully-enriched `services` array (every entry has `replaces` / `why` / `how` / `outcome` byte-identical to the markdown).
9. **Verify** with `wc -l` (doc) + the §7.2.4 Node.js script (HTML) + the §10 checklist (both artefacts).
10. **Report** back: file path, line count, reuse score, HTML enrichment count (`svcs:N enriched:N`), which prior services it depends on, and which components are retired.

---

## 12. One-shot prompt body (copy-paste for direct use)

```
You are a Salesforce Technical Architect working on the IBX PNM Apex Service
Framework migration. The repo at /Users/pkothapalli/Documents/IBXQA/IBXQA
contains five completed migration docs in requirements/Enhancements/ plus a
prompt.md describing the methodology and an interactive HTML mind map at
requirements/Enhancements/PNM_Modernization_MindMap.html. Your task is to
produce a new migration doc for the <FLOW NAME> guided flow that matches the
structure and depth of the five existing docs, AND to enrich the HTML mind
map with the new flow as a fully-expandable entry.

REQUIRED STEPS (do not skip any):

1. Read requirements/Enhancements/prompt.md fully. Honor every rule.
2. Run the discovery checklist in §2 of the prompt:
   - Glob for PRM*<X>* in omniScripts/, omniIntegrationProcedures/, classes/,
     lwc/, omniDataTransforms/
   - Read the DataPack JSON for each orchestrator IP
   - Read every Conditional Block element and capture the
     executionConditionalFormula verbatim
   - Read every DataRaptor Post / Extract / Transform / Turbo element
     and capture the bundle name
   - Read every Remote Action element and capture remoteClass.remoteMethod
   - Check classes/ for any existing PRM_<X>* Apex (Callable, Batch, Utils,
     Wrapper)
3. Build the element catalog table.
4. Build the INSERT and UPDATE inventories.
5. Build the variant axis cross-table.
6. Mark each element's Apex replacement using the running inventory in §5
   of the prompt (REUSE / EXTEND / NEW / STANDARDISE).
7. Compute the reuse score.
8. Write a placeholder file at
     requirements/Enhancements/PNM_<FlowName>_Apex_Service_Architecture.md
9. Use chunked StrReplace per §7.1 of the prompt to add all 13 sections in
   order. UNDER EVERY §6 SERVICE HEADING, include the four-callout block
   (Why we need it / How it helps / Outcome / Replaces) per §3.A of the
   prompt. No service heading may be missing any callout.
10. Enrich the HTML mind map per §7.2 of the prompt:
    - Add a new flow object to the FLOWS array (or replace the plain
      services list if the flow already exists as a stub).
    - The services array must include EVERY class from §4 of the markdown
      (reused + extended + new + standardise), each with
      { name, kind, note, replaces, why, how, outcome }.
    - The replaces / why / how / outcome strings must be byte-identical to
      the matching markdown §6 callouts.
    - Use the §7.2.3 placeholder + chunked StrReplace pattern when the
      services array is large (30+ entries).
11. Verify both artefacts:
    - wc -l on the markdown doc.
    - Run the §7.2.4 Node.js FLOWS-array verification — every flow must
      report enriched:N === svcs:N for the new flow.
    - ReadLints on the HTML — must be clean.
    - Walk the §10 checklist (10.1 markdown, 10.2 HTML).
12. Report back: file path, line count, total elements migrated, reuse score,
    HTML enrichment count, list of prior services this flow depends on,
    list of components retired.

DO NOT:
- Invent service names not in §5 of the prompt.
- Skip conditional formulas.
- Recommend rewriting existing Apex.
- Write the whole markdown doc in one Write call.
- Replace a 30+ service array in one StrReplace.
- Omit any of the four callout fields under any §6 service heading.
- Let the markdown §6 callouts diverge from the HTML services-array fields.
- Use emojis.

FLOW NAME: <fill in>
ENTRY OMNISCRIPT(S): <fill in if known, else discover>
SCOPE / SPECIAL NOTES: <fill in any user-supplied context>
```

---

## 13. When in doubt

- If a section doesn't apply (e.g. there's no external integration), include the section header and say "n/a — this flow has no external callouts".
- If you find unexpected complexity (e.g. an undocumented DR bundle calling out to a managed package), surface it explicitly in §10 Risks rather than glossing over it.
- If the existing Apex precedent is **broken** (e.g. a Batch with a known bug), document it as "kept verbatim — bug deferred to a separate user story" rather than silently fixing it.
- If you exhaust the discovery without finding a flow, ask the user one clarifying question — "I can find `PRM_Foo_English` and `PRM_Bar_English`, but no IP named `Foo`. Did you mean…?". Do this **once**, not repeatedly.
- If a flow is small enough that the doc would be <500 lines, still produce all 13 sections — they may be terse, but the structure is the contract.
- If the HTML services array exceeds ~25 entries and a single StrReplace fails with the JSON size error, switch to the §7.2.3 placeholder + chunked pattern; do not give up and partial-enrich.
- If a service is genuinely a one-line wrapper that doesn't merit a 4-sentence Why, still include all four callouts but keep them terse (one short sentence each). The pattern is mandatory; the depth is judgmental.
- If you see drift between the markdown §6 callouts and the HTML services-array fields (e.g. you edited one but not the other), treat it as a defect — fix it before reporting the work as done. The §7.2.4 Node.js verification + a quick `rg` for one of the strings in both files will surface drift in seconds.
