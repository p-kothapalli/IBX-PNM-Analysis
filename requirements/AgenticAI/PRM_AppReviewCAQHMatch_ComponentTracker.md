# Component Tracker — App Review CAQH Match (Idea 10)

**Feature:** Application Review CAQH Match — deterministic scoring of a credentialing application against CAQH, surfaced on a Case-record side panel.
**Design doc:** `requirements/AgenticAI/ideas/Idea10_App_Review_CAQH_Match_Agent.md`
**Agent spec:** `requirements/AgenticAI/PRM_AppReviewCAQHMatch-AgentSpec.md`
**Target org:** `IBXQA` (`prashanth.kothapalli@ibx.com.pie.qa`)
**Teardown script:** `scripts/remove_appreview_caqh_match.sh`

**Deploy status:** Panel set deployed to QA on 2026-06-12 (48/48 specified tests passed). The Agentforce agent bundle is **deployed, published and ACTIVE** in QA (agent **v5**, 2026-06-21) — branded **"Cred Agent"**, with detailed per-field findings, "Credentialing Specialist review" wording, and an **NPPES NPI check** wired into the match flow.

---

## 1. Apex classes (`force-app/main/default/classes/`)

| Class | Type | Deployed | Purpose |
|---|---|:---:|---|
| `PRM_CAQHMatchScoreService` | Service | ✅ | Deterministic field→section→overall match engine (normalization, Levenshtein, hard-fail rules, CMDT config) |
| `PRM_CAQHMatchScoreServiceTest` | Test | ✅ | Engine + invocable unit tests |
| `PRM_CAQHMatchScoreAction` | Invocable | ✅ | `@InvocableMethod` wrapper over the engine (aligned pairs → scorecard JSON + summary) |
| `PRM_AppReviewGatherAction` | Invocable | ✅ | Converts assembled review data (`omniDataJson`) / headless IP output into the engine's match-input payload via CMDT paths |
| `PRM_AppReviewGatherActionTest` | Test | ✅ | Gather + path-resolution + headless-mode unit tests |
| `PRM_AppReviewCaseAssembler` | Service | ✅ | **Server-side data assembly from a Case Id**: runs `PRM_FetchParDetails` + `PRM_ValidateCAQHAppReviewParent`, deep-merges to one `omniDataJson` (no OmniScript embedding). Has `@TestVisible` IP seams |
| `PRM_AppReviewCaseAssemblerTest` | Test | ✅ | Assembler + deep-merge + findValue unit tests |
| `PRM_AppReviewPersistDecisionAction` | Invocable | ✅ | Writes the scorecard to the audit objects (header + per-section steps) |
| `PRM_AppReviewPersistDecisionActionTest` | Test | ✅ | Persist + human-review gating + end-to-end unit tests |
| `PRM_AppReviewMatchController` | Controller | ✅ | `@AuraEnabled` for the LWC: `runMatch(caseId, omniDataJson)` (assembles server-side when blank) + `getLatestDecision(caseId)`. Resolves Case Numbers; now also surfaces practitioner NPI/first/last name |
| `PRM_AppReviewMatchControllerTest` | Test | ✅ | Controller (assembly path, view mapping, latest-decision) unit tests |
| `PRM_AppReviewAssembleAction` | Invocable | ✅ | Phase-1 agent action: DML-only application assembly from a Case Id/Number (no CAQH callout). Now also outputs `npi`/`firstName`/`lastName` for the NPPES check |
| `PRM_NpiNppesCheckAction` | Invocable | ✅ | **NPPES NPI check** — wraps `PRM_NpiValidationService.validatePractitionerNpi` (OmniStudio IP `PRM_ValidateNPIContainer`). Verifies the Individual NPI + name against the CMS NPI Registry; never throws, returns a specialist-routed `npiText` |
| `PRM_NpiNppesCheckActionTest` | Test | ✅ | NPI-check guard paths + null-list + never-throws unit tests |

## 2. Custom objects (`force-app/main/default/objects/`)

| Object | API name | Fields | Deployed | Purpose |
|---|---|:---:|:---:|---|
| Agent Decision (audit header) | `PRM_AgentDecision__c` | 22 | ✅ | One row per agent run — scores, human-review gate, decision memo, full scorecard snapshot. **Shared** AgenticAI audit object |
| Agent Decision Step (audit detail) | `PRM_AgentDecisionStep__c` | 15 | ✅ | One row per review section (master-detail to `PRM_AgentDecision__c`). **Shared** |
| CAQH Match Weight (config) | `PRM_CAQHMatchWeight__mdt` | 14 | ✅ | Per-field scoring config (weights, types, hard-fail rules, tolerances) **and** source paths (`PRM_CAQHPath__c`/`PRM_AppPath__c`) |

## 3. Custom Metadata records (`force-app/main/default/customMetadata/`)

Paths corrected on **2026-06-12** against the real server-assembled JSON for Case `500VB00000eCtksYAC` (CAQH source-of-truth lives under `Provider:*`; application data under the SF objects). Only fields with a reliable both-side anchor in the assembled payload are **active**; the rest are deactivated (`PRM_IsActive__c = false`) until the assembler is enriched to load their source steps.

| Record (`PRM_CAQHMatchWeight.*`) | Active | App path | CAQH path |
|---|:---:|---|---|
| `License_LicenseNumber` | ✅ | `PractitionerBusinessLicense:LicenseNumber` | `Provider:ProviderLicense:LicenseNumber` |
| `License_LicenseState` | ✅ | `PractitionerBusinessLicense:PRM_LicenseState__c` | `Provider:ProviderLicense:State` |
| `Specialty_NUCCTaxonomyCode` | ✅ | `PractitionerPrimarySpecialty:Taxonomy:TaxonomyCode` | `Provider:Specialty:NUCCTaxonomyCode` |
| `Specialty_SpecialtyName` | ✅ | `PractitionerPrimarySpecialty:Taxonomy:Name` | `Provider:Specialty:Specialty:SpecialtyName` |
| `Education_Institution` (now **Education - Degree**) | ✅ | `VerifyEducation:CAQHPersonEducation:EducationLevelSF` | `VerifyEducation:CAQHPersonEducation:CAQHEducationDegree` |
| `License_ExpirationDate` | ❌ | — | no SF expiration field in assembled payload |
| `License_LicenseStatus` | ❌ | — | no comparable CAQH license-status code |
| `DEA_DEANumber`, `DEA_ExpirationDate` | ❌ | — | app-side DEA not loaded by the assembler |
| `Malpractice_InsuranceCarrier`, `Malpractice_CoverageOccurrence` | ❌ | — | app-side malpractice not loaded by the assembler |

**11 records total; 5 active across 3 sections (License, Specialty, Education).** Verified end-to-end for Case `500VB00000eCtksYAC`: gather→score now resolves both App and CAQH values and produces a scorecard (the panel's "No data to compare" error is resolved).

> **Deployment note:** the file-based CustomMetadata deploy (`sf project deploy`) currently fails in this org with a server-side `UNKNOWN_EXCEPTION` (0 component errors, fresh ErrorId each attempt) while Apex deploys succeed. The 11 records were deployed via the **Apex Metadata API** (`Metadata.Operations.enqueueDeployment`) instead — DeployRequest jobs `0AfVB00000HOWEf0AP` / `0AfVB00000HOWkv0AH` succeeded. The CLI's REST `describe`/`query` cache was also stale during this work (reported existing fields/records as missing); trust **anonymous Apex** or the **Tooling API** for verification.

## 4. Lightning Web Component (`force-app/main/default/lwc/`)

| Bundle | Deployed | Purpose |
|---|:---:|---|
| `prmAppReviewCaqhMatch` (`.js`, `.html`, `.css`, `.js-meta.xml`) | ✅ | Case-record **side panel**: Run button → assembles data + scores + persists; renders overall score, per-section recommendation badges, App-vs-CAQH field diffs, hard-fail markers, human-review banner. Exposed on `lightning__RecordPage` (Case) + `lightning__AppPage` |

## 5. Agentforce agent bundle (`force-app/main/default/aiAuthoringBundles/`)

| Bundle | Deployed | Purpose |
|---|:---:|---|
| `PRM_App_Review_CAQH_Match` (`.agent`, `.bundle-meta.xml`) | ✅ **active v5** | **"Cred Agent"** employee agent. Label `Cred Agent` (API name unchanged for version-history stability). LLM slot-fills the Case Number → `assemble_case` → gather→score→**npi_nppes_check**→persist. Emits detailed `findingsText` (per-field missing/diff) and routes low/hard-flag results to a **Credentialing Specialist** (no "human" wording) |

---

## Reused existing components (NOT created by this feature — do not delete)

| Component | Type | Role |
|---|---|---|
| `PRM_ValidateCAQHAppReviewParent` | Integration Procedure | Live CAQH call (reused by the assembler) |
| `PRM_FetchParDetails` | Integration Procedure | Loads PractitionerForm + CAQH Id + NPI/name from the Case (reused by the assembler) |
| `PRMCAQHReviewTransform` | DataRaptor | App↔CAQH alignment (reused) |
| `PRM_NpiValidationService` | Apex service | NPPES NPI validation (reused by `PRM_NpiNppesCheckAction`) |
| `PRM_ValidateNPIContainer` | Integration Procedure | NPPES registry callout behind `PRM_NpiValidationService` (reused) |

---

## Post-deploy follow-ups

- [x] **Confirm CMDT paths** against a real merged IP response captured in QA — done 2026-06-12 against Case `500VB00000eCtksYAC`; 5 fields repointed to live nodes, 6 unmappable fields deactivated.
- [ ] **Enrich `PRM_AppReviewCaseAssembler`** to also load app-side DEA, malpractice/insurance, and license expiration/status (additional IP/DataRaptor steps) so the 6 deactivated fields can be re-enabled with both-side anchors.
- [ ] Add the `prmAppReviewCaqhMatch` panel to the Case Lightning record page (App Builder).
- [ ] Grant access to `PRM_AppReviewMatchController` (+ the audit objects) via the credentialing permission set.
- [ ] Enable Agentforce/Einstein in QA, then deploy the agent bundle + build the `AiEvaluationDefinition` eval suite.
- [ ] Seed the remaining CMDT sections (Work History, Board Certification, CDS).
