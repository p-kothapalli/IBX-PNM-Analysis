# User Story Architect Agent — Detailed Approach

## Vision

Build an AI agent ("User Story Architect") that helps Solution Architects, Technical Architects, and Consultants write in-depth, implementation-ready user stories for Salesforce Health & Life Sciences (HLS) and Provider Network Management (PNM) projects. The agent understands OmniStudio components, asks clarifying questions before generating output, and produces stories in the same format and depth as the existing `requirements/` documents in this repo.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Target Personas](#2-target-personas)
3. [Agent Capabilities](#3-agent-capabilities)
4. [Architecture Overview](#4-architecture-overview)
5. [Vertical Selection — Industry Cloud First](#5-vertical-selection--industry-cloud-first)
6. [Conversation Flow — Question-First Approach](#6-conversation-flow--question-first-approach)
7. [User Story Output Format](#7-user-story-output-format)
8. [OmniStudio Component Knowledge Base](#8-omnistudio-component-knowledge-base)
9. [MCP Server Design](#9-mcp-server-design)
10. [Skill, Rule & Agent Definitions](#10-skill-rule--agent-definitions)
11. [Integration with AI Expert Suite](#11-integration-with-ai-expert-suite)
12. [Knowledge Sources & RAG](#12-knowledge-sources--rag)
13. [Implementation Phases](#13-implementation-phases)
14. [Directory Structure](#14-directory-structure)
15. [Registry Entry](#15-registry-entry)
16. [Example Interaction](#16-example-interaction)
17. [Risk & Mitigation](#17-risk--mitigation)

---

## 1. Problem Statement

Writing implementation-ready user stories for Salesforce HLS/PNM projects is time-consuming and requires deep knowledge of:
- OmniStudio components (OmniScript, FlexCard, DataRaptor, Integration Procedure, DataMapper, Decision Matrix)
- Salesforce Health Cloud object model (IndividualApplication, HealthcareFacility, HealthcarePractitionerFacility, etc.)
- Industry-specific workflows (credentialing, provider change, off-cycle, PSV, QC, committee review)
- Existing codebase patterns (element naming, DataRaptor conventions, IP chaining)

Today, architects spend 2–4 hours per user story. This agent should reduce that to 15–30 minutes of guided conversation.

---

## 2. Target Personas

| Persona | How They Use the Agent |
|---------|----------------------|
| **Solution Architect (SA)** | Describes a business requirement in natural language; agent produces a complete user story with technical section |
| **Technical Architect (TA)** | Provides an existing OmniScript name or flow; agent analyzes current state and proposes changes |
| **Consultant** | Selects a vertical (HLS, PNM) and describes a capability; agent maps it to Salesforce components |
| **Business Analyst** | Reviews agent-generated stories for acceptance criteria completeness |
| **Developer** | Uses the technical section (component changes, DataRaptor specs, Apex class references) as a build spec |

---

## 3. Agent Capabilities

### 3.1 Core Capabilities

| # | Capability | Description |
|---|-----------|-------------|
| C1 | **Vertical Selection** | Prompt user to choose industry vertical (HLS, PNM, Insurance, Financial Services, etc.) before generating stories |
| C2 | **Clarifying Questions** | Ask 5–10 targeted questions about the requirement before generating any output |
| C3 | **Current-State Analysis** | Read existing OmniScript/FlexCard metadata from the codebase to understand what exists today |
| C4 | **User Story Generation** | Produce stories in the format: Persona → Story → Why It Matters → Technical Section → Acceptance Criteria |
| C5 | **OmniStudio Component Mapping** | Map business requirements to specific OmniStudio components with element-level detail |
| C6 | **Impact Analysis** | Identify all OmniScripts, DataRaptors, IPs, and Apex classes affected by a proposed change |
| C7 | **Implementation Plan** | Generate phased implementation plans with dependencies and effort estimates |
| C8 | **Acceptance Criteria in Gherkin** | Generate Given/When/Then acceptance criteria |
| C9 | **Clarification Questions Table** | Generate a table of questions for Product/Business owners with impact and owner columns |
| C10 | **Cross-Story Dependency Detection** | Identify when a new story depends on or conflicts with existing stories in the repo |

### 3.2 OmniStudio-Specific Capabilities

| # | Capability | Description |
|---|-----------|-------------|
| O1 | **OmniScript Flow Design** | Propose step-by-step OmniScript flow with elements, conditions, and navigation |
| O2 | **DataRaptor Spec** | Generate Extract/Transform/Load DataRaptor specifications with field mappings |
| O3 | **Integration Procedure Chain** | Design IP chains with execution order, conditions, and response mapping |
| O4 | **FlexCard Layout** | Propose FlexCard layouts with data sources, actions, and child cards |
| O5 | **DataMapper Transformation** | Define input/output mappings for DataMapper components |
| O6 | **Decision Matrix Rules** | Generate decision matrix entries for conditional business logic |
| O7 | **Element Naming Convention** | Follow existing naming patterns (e.g., `PRM_` prefix, `_English` suffix, `DR`/`IP`/`SV_` prefixes) |

---

## 4. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    USER (in Cursor / Claude Code)           │
│                                                             │
│   "I need a user story for adding Georgia as a new state    │
│    to the credentialing flow"                               │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   SKILL: user-story-architect                │
│                                                             │
│  1. Detects "user story" / "requirement" / "story" intent   │
│  2. Loads SKILL.md with vertical knowledge + output format  │
│  3. Triggers question-first conversation flow               │
└─────────────────────────┬───────────────────────────────────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐
│  MCP Server  │ │   RAG Tool   │ │  Codebase Analysis   │
│  (Tools)     │ │  (Knowledge) │ │  (Grep/Read/Glob)    │
│              │ │              │ │                      │
│ - vertical   │ │ - OmniStudio │ │ - Read OmniScript    │
│   selector   │ │   docs       │ │   element JSONs      │
│ - question   │ │ - HLS object │ │ - Find DataRaptors   │
│   generator  │ │   model      │ │ - Analyze IPs        │
│ - story      │ │ - PNM flows  │ │ - Existing stories   │
│   formatter  │ │ - Patterns   │ │   in requirements/   │
│ - impact     │ │              │ │                      │
│   analyzer   │ │              │ │                      │
└──────────────┘ └──────────────┘ └──────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  OUTPUT: User Story (.md file)               │
│                                                             │
│  - Persona, Story, Why It Matters                           │
│  - Technical Section (Current State, Changes, Examples)     │
│  - Acceptance Criteria (Gherkin)                            │
│  - Clarification Questions table                            │
│  - Impact Analysis table                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Vertical Selection — Industry Cloud First

The agent must ask which vertical the user is working in **before** diving into user story details. Each vertical loads different context:

### Supported Verticals

| Vertical | Salesforce Cloud | Key Objects | OmniStudio Patterns |
|----------|-----------------|-------------|-------------------|
| **Provider Network Management (PNM)** | Health Cloud + PNM Managed Package | IndividualApplication (Case Manager), HealthcareFacility, HealthcarePractitionerFacility, Account (Vendor/Practitioner), HealthcareProviderNpi, Identifier | `PRM_` prefixed OmniScripts, DataRaptors (PRMDRxxx), IPs (PRM_xxx), PAR/Off Cycle/Recred flows |
| **Health & Life Sciences (HLS)** | Health Cloud | CarePlan, CareProgram, Patient, EHR objects, Clinical data | HLS-specific OmniScripts, patient intake flows |
| **Insurance** | Vlocity Insurance | Policy, Quote, Claim, InsuranceProduct, Coverage | Insurance quoting OmniScripts, rating procedures |
| **Financial Services** | Financial Services Cloud | FinancialAccount, Lead, Opportunity, Wealth Mgmt objects | Advisory flows, client onboarding OmniScripts |
| **Communications & Media** | Vlocity CME | Order, Product, ServiceAccount, Subscription | CPQ OmniScripts, order management flows |
| **Custom / Generic** | Platform | Any standard/custom objects | User-defined OmniScript patterns |

### Vertical Selection Flow

```
Agent: "Which Salesforce vertical are you working in?"

  1. Provider Network Management (PNM)
  2. Health & Life Sciences (HLS)
  3. Insurance
  4. Financial Services
  5. Communications & Media
  6. Custom / Other

User: "1 - PNM"

Agent: "Great. PNM context loaded. I now understand:
  - OmniScript naming: PRM_ prefix
  - Key objects: IndividualApplication, HealthcareFacility, etc.
  - DataRaptor patterns: PRMDRxxx, PRMDR_Fetchxxx
  - IP patterns: PRM_xxxParent → PRM_xxx
  - Existing flows in your codebase: [lists discovered flows]

  Now, tell me about the requirement you want to create a user story for."
```

---

## 6. Conversation Flow — Question-First Approach

The agent MUST ask clarifying questions before generating a user story. This is the core differentiator.

### Phase 1: Vertical & Context (2–3 questions)

| # | Question | Purpose |
|---|----------|---------|
| Q1 | Which Salesforce vertical? (PNM / HLS / Insurance / etc.) | Load vertical-specific knowledge |
| Q2 | What is the high-level business capability? (e.g., "Add a new state to credentialing") | Scope the story |
| Q3 | Is this a new feature, enhancement to existing, or bug fix? | Determine story structure |

### Phase 2: Business Requirements (3–5 questions)

| # | Question | Purpose |
|---|----------|---------|
| Q4 | Who is the primary user persona? (Credentialing Specialist, PDM Specialist, Broker, etc.) | Story "As a..." |
| Q5 | What is the business outcome? Why does this matter? | Story "So that..." |
| Q6 | Are there regulatory, compliance, or SLA requirements? | Non-functional requirements |
| Q7 | What is the priority? (P0 = must-have, P1 = should-have, P2 = nice-to-have) | Prioritization |
| Q8 | Are there related user stories already written? | Cross-reference existing stories |

### Phase 3: Technical Discovery (3–5 questions)

| # | Question | Purpose |
|---|----------|---------|
| Q9 | Which OmniScript(s) or guided flow(s) are affected? (or "I don't know") | Map to components |
| Q10 | Does this involve new Salesforce objects/fields, or changes to existing? | Object model impact |
| Q11 | Are there external integrations (APIs, Precisely, NPDB, CAQH)? | Integration scope |
| Q12 | Should the agent analyze the current codebase for impacted components? | Trigger codebase scan |
| Q13 | Are there specific DataRaptors or Integration Procedures you know are involved? | Narrow technical scope |

### Phase 4: Acceptance & Validation (2–3 questions)

| # | Question | Purpose |
|---|----------|---------|
| Q14 | What does "done" look like from the business user's perspective? | Acceptance criteria |
| Q15 | Are there edge cases or error scenarios to cover? | Negative test cases |
| Q16 | Who needs to review/approve this story? (Product, Legal, Ops, Technical) | Stakeholder alignment |

### Question Adaptation

The agent should **adapt** questions based on previous answers. For example:
- If user says "PNM" vertical → skip generic HLS questions, ask PNM-specific questions about Case Manager, PAR, Off Cycle, etc.
- If user says "enhancement to existing OmniScript" → ask which OmniScript, then scan the codebase for current state
- If user says "I don't know which components" → agent scans the codebase and proposes likely candidates

---

## 7. User Story Output Format

Based on analysis of 19 existing user stories in `requirements/`, the agent should produce stories in this format:

```markdown
# USER STORY [N]: [Title]

**Persona:** [Role], Developer
**Priority:** P[0-2]
**OmniScript:** [OmniScript API Name(s)]
**Relevant Requirements:** [Reference IDs]

## Story

**As a** [persona],
**I want** [capability],
**So that** [business outcome].

**Why it matters:** [Business context and impact]

## Technical Section (For Developers)

### Current State (from codebase)

- **[Component Name]** ([Type]): [Current behavior]
- **Location:** `[file path or element name]`

### Changes

| Component | Type | Change |
|-----------|------|--------|
| **[Name]** | [OmniScript Element / DataRaptor / IP / Apex / Field] | [What to do] |

### Example (if applicable)

```json
// JSON example of configuration change
```

### DataRaptor / Integration Procedure Specifications

| DR/IP Name | Type | Input | Output | Change |
|-----------|------|-------|--------|--------|
| [Name] | Extract/Transform/Load/IP | [Fields] | [Fields] | [Modification] |

## Acceptance Criteria

**Given** [precondition],
**When** [action],
**Then** [expected result].

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | [Question] | [What it affects] | [Technical / BA / Legal / Ops] |

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| [Name] | [OmniScript / DataRaptor / IP / Apex / Object] | [HIGH / MEDIUM / LOW] | [Description] |
```

---

## 8. OmniStudio Component Knowledge Base

The agent's SKILL.md must contain a reference section teaching the LLM about OmniStudio components. This is the "domain knowledge" that generic LLMs lack.

### Component Reference

| Component | What It Is | When to Use | Key Properties |
|-----------|-----------|-------------|----------------|
| **OmniScript** | Guided UI flow (multi-step form) | User-facing data collection, guided processes | Steps, Elements, Conditions, Navigation, Embedded OS |
| **FlexCard** | Data display component (card/tile) | Record display, dashboards, summary views | Data Sources, Actions, Conditions, Child Cards, States |
| **DataRaptor Extract** | Read data from Salesforce | Fetch records for display in OmniScript/FlexCard | SObject, Fields, Filters, Relationships, Output JSON |
| **DataRaptor Transform** | Transform JSON | Reshape data between components | Input/Output mapping, Formulas, Conditions |
| **DataRaptor Load** | Write data to Salesforce | Create/Update/Upsert records from OmniScript | SObject, Fields, Mapping, Upsert Key |
| **Integration Procedure (IP)** | Server-side orchestration | Chain multiple DataRaptors, Apex, HTTP callouts | Elements: DR Extract/Load/Transform, Remote Action, Matrix, Conditions |
| **DataMapper** | Declarative data transformation | Map fields between source and target | Input/Output schemas, Field mappings, Transformations |
| **Decision Matrix** | Lookup/rule table | Business rules, pricing, routing logic | Dimensions (inputs), Output columns, Versioning |

### Naming Conventions (PNM-Specific)

| Pattern | Example | Meaning |
|---------|---------|---------|
| `PRM_[Name]_English` | `PRM_ProviderChangeForm_English` | OmniScript (English locale) |
| `PRMDR[Action][Object]` | `PRMDRUpdateAccountPDM` | DataRaptor (Update Account for PDM) |
| `PRM_[Name]` | `PRM_PDMRecordsCreation` | Integration Procedure |
| `PRM_[Name]Parent` | `PRM_FetchDetailsParent` | Parent IP (chains child IPs) |
| `SV_[Name]` | `SV_PNC` | Set Values element in OmniScript |
| `IP[Name]` | `IPCreatePDMRecords` | IP Action element in OmniScript |
| `DR[Name]` | `DRUpdateAccount` | DataRaptor element in IP |

### OmniScript Element Types

| Element Type | Purpose | Example |
|-------------|---------|---------|
| Step | Container for form fields | `ServiceAreaVerificationStep` |
| Text Block | Display-only text/HTML | `TextBlockCa` |
| Type Ahead | Autocomplete search | `HCFTypeAhead` |
| Select / Radio | Options selection | `PractitionerState` |
| Checkbox | Boolean toggle | `CBPNCCkd` |
| Set Values | Assign data to JSON | `SV_PNC` |
| DataRaptor Post Action | Save data | `DRUpdateHealthcareFacilityPNC` |
| IP Action | Call Integration Procedure | `IPCreatePDMRecords` |
| Navigate Action | Redirect after completion | `NavigateToCaseManager` |
| Conditional | Show/hide based on logic | `show: IsRecredentialing = true` |
| Embedded OmniScript | Nest another OmniScript | `ProviderChangeFormCapitationSite` |
| Repeat | Repeatable block (max N) | `PLRecredBlock` (max 4) |

---

## 9. MCP Server Design

The agent uses an MCP server to provide tools that the LLM cannot do natively.

### Tools

| Tool Name | Description | Parameters | Returns |
|-----------|-------------|-----------|---------|
| `select_vertical` | Set the active vertical and load context | `vertical: string` | Vertical config, object model, naming conventions |
| `analyze_omniscript` | Parse an OmniScript's elements from codebase | `omniscript_name: string` | Steps, elements, conditions, data flow |
| `find_impacted_components` | Search codebase for all components affected by a change | `object_name: string, field_name: string` | List of OmniScripts, DataRaptors, IPs, Apex referencing this object/field |
| `generate_questions` | Generate clarifying questions based on partial requirement | `requirement_text: string, vertical: string` | Ordered list of questions with impact and owner |
| `format_user_story` | Format structured data into the standard user story template | `story_data: object` | Formatted markdown |
| `search_existing_stories` | Search `requirements/` folder for related stories | `keywords: string[]` | Matching stories with relevance score |
| `get_object_model` | Return the Salesforce object model for the active vertical | `vertical: string` | Objects, fields, relationships |
| `validate_story_completeness` | Check if a story has all required sections | `story_markdown: string` | Completeness score, missing sections |

### MCP Server Implementation

```
mcp-server/
├── src/
│   ├── index.py                    # FastMCP server entry point
│   ├── tools/
│   │   ├── vertical_selector.py    # Vertical config loader
│   │   ├── codebase_analyzer.py    # OmniScript/DR/IP parser
│   │   ├── question_generator.py   # Clarifying question engine
│   │   ├── story_formatter.py      # Markdown template engine
│   │   ├── impact_analyzer.py      # Cross-component impact detection
│   │   └── story_searcher.py       # Existing story search
│   ├── knowledge/
│   │   ├── verticals/
│   │   │   ├── pnm.yaml           # PNM object model + patterns
│   │   │   ├── hls.yaml           # HLS object model + patterns
│   │   │   ├── insurance.yaml     # Insurance patterns
│   │   │   └── fsc.yaml           # Financial Services patterns
│   │   ├── omnistudio/
│   │   │   ├── components.yaml    # Component reference
│   │   │   ├── naming.yaml        # Naming conventions
│   │   │   └── patterns.yaml      # Common patterns
│   │   └── templates/
│   │       ├── user_story.md      # Story template
│   │       ├── impact_analysis.md # Impact template
│   │       └── implementation.md  # Implementation plan template
│   └── utils/
│       ├── codebase_reader.py     # File system utilities
│       └── json_parser.py         # OmniScript JSON parser
├── pyproject.toml
├── setup_uv_env.sh
└── README.md
```

---

## 10. Skill, Rule & Agent Definitions

### 10.1 Skill: `user-story-architect`

**File:** `skills/user-story-architect/SKILL.md`

The SKILL.md is the most important file — it teaches the LLM how to behave. Key sections:

```yaml
---
description: >
  Generates implementation-ready user stories for Salesforce projects.
  Use when the user asks to create, write, or draft a user story, requirement,
  technical specification, or implementation plan for Salesforce features
  including OmniStudio, Health Cloud, PNM, Insurance, or Financial Services.
globs:
  - "requirements/**/*.md"
  - "force-app/**/omniScripts/**"
  - "force-app/**/dataRaptors/**"
  - "force-app/**/integrationProcedures/**"
---
```

**Body content (summarized):**
1. Always ask which vertical first
2. Always ask clarifying questions before generating (minimum 5)
3. Scan the codebase for current state when the user mentions existing components
4. Follow the output format exactly (Section 7 above)
5. Include OmniStudio component-level detail in the technical section
6. Generate clarification questions for Product/Business
7. Use naming conventions specific to the selected vertical
8. Reference existing stories in `requirements/` when relevant

### 10.2 Rules

**File:** `rules/story-completeness-check.md`

```yaml
---
description: >
  Ensures generated user stories have all required sections:
  Persona, Story, Technical Section, Acceptance Criteria, and
  Clarification Questions. Fires after story generation.
globs:
  - "requirements/**/*.md"
---
```

**Body:** Check that every generated user story includes: Persona, Priority, OmniScript reference, Story (As a/I want/So that), Technical Section with Current State and Changes table, Acceptance Criteria in Gherkin, and Clarification Questions table.

**File:** `rules/omnistudio-naming.md`

```yaml
---
description: >
  Enforces OmniStudio naming conventions. PNM components must use PRM_ prefix.
  DataRaptors must use PRMDR prefix. Integration Procedures must use PRM_ prefix.
globs:
  - "requirements/**/*.md"
  - "force-app/**/omniScripts/**"
---
```

### 10.3 Agent: `story-reviewer`

**File:** `agents/story-reviewer/AGENT.md`

A sub-agent that reviews generated stories for:
- Technical accuracy (do referenced components exist in codebase?)
- Completeness (all sections present?)
- Consistency (naming conventions followed?)
- Cross-story conflicts (does this contradict existing stories?)

---

## 11. Integration with AI Expert Suite

### Option A: Register as an Expert (Recommended)

Package the agent as a proper AI Expert Suite expert and register it in the central registry.

**Benefits:**
- Auto-updates across Cursor and Claude Code
- Shows up in AI Suite UI for easy enable/disable
- Dynamic tool loading (only loads when user story work is detected)
- Telemetry and quality monitoring

**Process:**
1. Create a Git repo on `git.soma.salesforce.com` (e.g., `c360-ai-tooling/user-story-architect`)
2. Structure it as an Expert with `skills/`, `rules/`, `agents/` directories
3. Add MCP server for tools
4. Submit a PR to [expert-registry `registry.yaml`](https://git.soma.salesforce.com/c360-ai-tooling/expert-registry/blob/master/registry.yaml)
5. Contact `#ai-dev-suite-community` for review

**Registry entry:**

```yaml
experts:
  - id: user-story-architect
    name: User Story Architect
    description: >
      Generates implementation-ready user stories for Salesforce projects
      with OmniStudio component mapping, impact analysis, and vertical-specific
      knowledge. Use when creating requirements, user stories, or technical
      specifications for HLS, PNM, Insurance, or Financial Services.
    github: https://git.soma.salesforce.com/[your-org]/user-story-architect.git
    branch: v0.1.0
    tags: [user-stories, requirements, omnistudio, hls, pnm]
    links:
      docs: https://git.soma.salesforce.com/pages/[your-org]/user-story-architect/
      slack: https://salesforce.enterprise.slack.com/archives/[channel-id]
    expert_dir: src/expert
    install: uv sync
    mcp:
      type: local
      runtime: python
      command: uv run python -m src.mcp_server --port 29120
      port: 29120
      settings:
        - name: Default Vertical
          env: DEFAULT_VERTICAL
          default: pnm
          required: false
```

### Option B: Local Expert (Quick Start)

For rapid prototyping, create the expert locally in your workspace without registering it.

**Process:**
1. Create `.cursor/skills/user-story-architect/SKILL.md` in your project
2. Create `.cursor/rules/` for rules
3. Cursor will automatically pick them up
4. No MCP server needed for the basic version — the LLM uses built-in tools (Read, Grep, Glob)

---

## 12. Knowledge Sources & RAG

The agent needs domain knowledge beyond what the LLM has in its training data.

### Static Knowledge (embedded in SKILL.md or references/)

| Source | What It Contains | How to Use |
|--------|-----------------|-----------|
| `references/omnistudio-components.md` | Full OmniStudio component reference | Loaded when vertical is selected |
| `references/pnm-object-model.md` | PNM object model with relationships | Loaded when PNM vertical is selected |
| `references/hls-object-model.md` | HLS object model | Loaded when HLS vertical is selected |
| `references/naming-conventions.md` | Naming patterns per vertical | Always loaded |
| `references/story-examples.md` | 3–5 exemplar user stories from this repo | Loaded as few-shot examples |

### Dynamic Knowledge (via MCP tools)

| Source | What It Provides | How to Access |
|--------|-----------------|--------------|
| **Codebase scan** | Current OmniScript elements, DataRaptors, IPs in force-app/ | `analyze_omniscript` tool → Grep/Read/Glob |
| **Existing stories** | Previously written stories in requirements/ | `search_existing_stories` tool → Glob + Read |
| **Salesforce internal docs** | OmniStudio documentation, HLS guides | `search_search` via mcp-adaptor |
| **CAQH / NPDB patterns** | External integration patterns | Embedded in references/ |

### RAG Strategy (Future Enhancement)

For v2, index the following into a vector store:
1. All files in `requirements/` (existing stories as examples)
2. All OmniScript element JSON files in `force-app/`
3. OmniStudio public documentation
4. Health Cloud developer guide

Use the `search_search` MCP tool (mcp-adaptor) for real-time Salesforce internal doc retrieval.

---

## 13. Implementation Phases

### Phase 1: Local Skill (Week 1–2) — MVP

**Goal:** Working agent in Cursor that asks questions and generates user stories using built-in tools only.

| Task | Description | Effort |
|------|-------------|--------|
| 1.1 | Create `SKILL.md` with vertical selection, question flow, and output format | 2 days |
| 1.2 | Create `references/` with OmniStudio component reference and PNM object model | 1 day |
| 1.3 | Create `references/story-examples.md` with 3 exemplar stories from this repo | 0.5 day |
| 1.4 | Create rules for completeness check and naming conventions | 0.5 day |
| 1.5 | Test with 5 real requirements from the project | 1 day |
| 1.6 | Iterate on SKILL.md based on output quality | 2 days |

**Deliverable:** `.cursor/skills/user-story-architect/SKILL.md` + `references/`

### Phase 2: MCP Server (Week 3–4) — Enhanced

**Goal:** Add MCP tools for codebase analysis, impact detection, and story search.

| Task | Description | Effort |
|------|-------------|--------|
| 2.1 | Create Python MCP server with FastMCP | 1 day |
| 2.2 | Implement `analyze_omniscript` tool (parse element JSONs) | 2 days |
| 2.3 | Implement `find_impacted_components` tool (cross-reference search) | 2 days |
| 2.4 | Implement `search_existing_stories` tool | 0.5 day |
| 2.5 | Implement `select_vertical` with config loading | 1 day |
| 2.6 | Integration testing with real OmniScript metadata | 1 day |

**Deliverable:** MCP server running locally on port 29120

### Phase 3: AI Expert Suite Registration (Week 5) — Distribution

**Goal:** Package as an Expert and register in the AI Suite for team-wide use.

| Task | Description | Effort |
|------|-------------|--------|
| 3.1 | Create Git repo on git.soma.salesforce.com | 0.5 day |
| 3.2 | Structure as Expert (skills/, rules/, agents/, mcp server) | 1 day |
| 3.3 | Write README and documentation | 0.5 day |
| 3.4 | Submit PR to expert-registry | 0.5 day |
| 3.5 | Team testing and feedback | 2 days |

**Deliverable:** Expert available in AI Suite UI for the team

### Phase 4: RAG + Multi-Vertical (Week 6–8) — Advanced

**Goal:** Add vector search, additional verticals, and story-reviewer sub-agent.

| Task | Description | Effort |
|------|-------------|--------|
| 4.1 | Index existing stories and OmniScript metadata into vector store | 2 days |
| 4.2 | Add Insurance and FSC vertical configs | 2 days |
| 4.3 | Build story-reviewer sub-agent | 2 days |
| 4.4 | Add implementation plan generation | 2 days |
| 4.5 | Integration with Agent Exchange for discovery | 1 day |

---

## 14. Directory Structure

### Full Expert Package

```
user-story-architect/
├── src/
│   └── expert/
│       ├── skills/
│       │   └── user-story-architect/
│       │       ├── SKILL.md                          # Main skill instructions
│       │       ├── references/
│       │       │   ├── omnistudio-components.md       # Component reference
│       │       │   ├── pnm-object-model.md           # PNM objects & relationships
│       │       │   ├── hls-object-model.md            # HLS objects & relationships
│       │       │   ├── naming-conventions.md          # Per-vertical naming rules
│       │       │   ├── story-examples.md              # 3–5 exemplar stories
│       │       │   └── question-templates.md          # Question bank per vertical
│       │       └── scripts/
│       │           └── validate_story.py              # Story completeness checker
│       ├── rules/
│       │   ├── story-completeness-check.md
│       │   ├── omnistudio-naming.md
│       │   └── acceptance-criteria-format.md
│       └── agents/
│           └── story-reviewer/
│               └── AGENT.md
├── src/
│   ├── index.py                                      # FastMCP server
│   ├── tools/
│   │   ├── vertical_selector.py
│   │   ├── codebase_analyzer.py
│   │   ├── question_generator.py
│   │   ├── story_formatter.py
│   │   ├── impact_analyzer.py
│   │   └── story_searcher.py
│   └── knowledge/
│       └── verticals/
│           ├── pnm.yaml
│           ├── hls.yaml
│           └── insurance.yaml
├── pyproject.toml
├── setup_uv_env.sh
└── README.md
```

### Quick Start (Phase 1 — Local Only)

```
.cursor/
├── skills/
│   └── user-story-architect/
│       ├── SKILL.md
│       └── references/
│           ├── omnistudio-components.md
│           ├── pnm-object-model.md
│           └── story-examples.md
└── rules/
    ├── story-completeness-check.md
    └── omnistudio-naming.md
```

---

## 15. Registry Entry

For AI Expert Suite registration (Phase 3):

```yaml
experts:
  - id: user-story-architect
    name: User Story Architect
    description: >
      Generates implementation-ready Salesforce user stories with OmniStudio
      component mapping, vertical-specific knowledge (PNM, HLS, Insurance, FSC),
      impact analysis, and question-first conversation flow. Use when creating
      requirements, user stories, or technical specs.
    github: https://git.soma.salesforce.com/[your-org]/user-story-architect.git
    branch: v0.1.0
    expert_dir: src/expert
    install: uv sync
    tags:
      - user-stories
      - requirements
      - omnistudio
      - hls
      - pnm
      - architecture
    links:
      docs: https://git.soma.salesforce.com/pages/[your-org]/user-story-architect/
      slack: https://salesforce.enterprise.slack.com/archives/[your-channel]
    mcp:
      type: local
      runtime: python
      command: >
        OTEL_SERVICE_NAME=user-story-architect
        uv run python -m src.index --port 29120
      port: 29120
      settings:
        - name: Default Vertical
          env: DEFAULT_VERTICAL
          default: pnm
          required: false
        - name: Requirements Path
          env: REQUIREMENTS_PATH
          default: requirements/
          required: false
    aliases:
      - name: validate-story
        runtime: python
        command: uv run python -m src.expert.skills.user-story-architect.scripts.validate_story
```

---

## 16. Example Interaction

### Scenario: Adding Georgia to the Credentialing Flow

```
User: "I need to create user stories for adding Georgia as a new state
       to the credentialing system"

Agent: "Let me help you create implementation-ready user stories for this.
        First, a few questions:

        **Vertical & Context**
        1. I see this workspace is a PNM (Provider Network Management) project.
           Is that correct?
        2. Is this a new feature or enhancement to existing flows?

User: "Yes PNM, enhancement to existing"

Agent: "Got it. I've loaded PNM context. Let me scan your codebase...

        I found 12 OmniScripts with PRM_ prefix, including:
        - PRM_PractitionerParticipationForm_English
        - PRM_CredApplicationReviewSubOS_English
        - PRM_PSVSubOsWSNPDB_English
        - PRM_RecredQC_English
        - PRM_ProviderChangeForm_English

        **Business Requirements**
        3. Which specific credentialing flows need Georgia? All of the above,
           or a subset?
        4. What counties in Georgia need to be supported?
        5. Are there GA-specific compliance requirements (e.g., CDS verification,
           admitting privileges)?
        6. Is there a new provider participation form specific to Georgia?

User: "All flows. Counties: Fulton, Cobb, Clayton, DeKalb, Gwinnett.
       Need to check on CDS and admitting privileges. Yes, there's a new
       form called 'Provider Participation Form AH GA'."

Agent: "Perfect. A few more technical questions:

        **Technical Discovery**
        7. I found PractitionerState in AddLicenseBlock uses optionSource:
           Address.PRM_State__c. Should GA be added to the picklist values
           on that field, or hardcoded in the OmniScript options array?
        8. The DEAState and CDSState fields in PSV flows are readOnly and
           populated from DataRaptors. Should GA just flow through, or do
           we need new verification URLs?
        9. Should I generate separate user stories per OmniScript, or one
           story per logical change area?

User: "Add to picklist. Need to verify GA CDS. Separate stories per area."

Agent: [Generates 7 user stories in the standard format, with:
        - Technical sections referencing specific OmniScript elements
        - DataRaptor change specifications
        - Clarification questions for Legal/Ops
        - Impact analysis table
        - Acceptance criteria in Gherkin format]
```

This matches the depth and format of `GA_Internal_Credentialing_User_Stories.md` — because that's exactly what it was trained on.

---

## 17. Risk & Mitigation

| # | Risk | Impact | Mitigation |
|---|------|--------|-----------|
| R1 | LLM generates incorrect OmniScript element names | Developer builds wrong thing | `analyze_omniscript` tool validates against actual codebase; story-reviewer agent cross-checks |
| R2 | Agent doesn't ask enough questions, produces generic stories | Rework and back-and-forth | SKILL.md enforces minimum 5 questions; completeness rule catches missing sections |
| R3 | Vertical context is wrong (e.g., PNM patterns applied to Insurance) | Incorrect technical section | Strict vertical selection at start; different reference files per vertical |
| R4 | Agent hallucinates DataRaptor or IP names | Developer confusion | MCP tool verifies component existence in codebase before including in output |
| R5 | Stories become stale as codebase evolves | Drift between stories and reality | Agent always reads current codebase (not cached); timestamps on stories |
| R6 | SKILL.md exceeds context window | Performance degradation | Use references/ for large docs (loaded on demand); keep SKILL.md under 10K tokens |
| R7 | Team adoption is low | Investment not realized | Start with Phase 1 (local, zero setup); gather feedback before building MCP server |

---

## Appendix A: Key Internal Resources

| Resource | URL | Purpose |
|----------|-----|---------|
| AI Expert Suite Docs | https://git.soma.salesforce.com/pages/c360-ai-tooling/c360-ai-tooling-docs/ | Expert packaging, registry, skills, rules |
| Expert Registry | https://git.soma.salesforce.com/c360-ai-tooling/expert-registry/blob/master/registry.yaml | Register your Expert |
| Agent Exchange | https://agentexchange.internal.salesforce.com/ | Discover existing agents |
| DX MCP Exchange | https://falcon.devhub.internal.salesforce.com/aihub/mcp-exchange | Discover MCP servers |
| AI Paved Path - Testing & Quality | https://git.soma.salesforce.com/pages/c360-ai-tooling/ai-paved-path/docs/Testing-and-Quality/ | Testing patterns |
| #ai-dev-suite-community | https://salesforce.enterprise.slack.com/archives/C099KN7D6HY | Support channel |
| #community-cursor | https://salesforce.enterprise.slack.com/archives/C08KSG76MMJ | Cursor community |
| QTA Full Documentation | https://docs.google.com/document/d/1JyyzUS7RMJP-g4iVNSPKAZysdz_SliJ_vzX842C5LaU/edit | QTA reference implementation |

## Appendix B: Comparison with QTA Architecture

| Aspect | QTA (Quality Test Agent) | User Story Architect |
|--------|-------------------------|---------------------|
| **Purpose** | Execute QA tests via browser automation | Generate user stories via conversation |
| **Input** | Natural language test prompt or GUS Test Suite | Natural language requirement description |
| **Output** | HTML test execution report (pass/fail) | Markdown user story document |
| **MCP Server** | qta-core (LLM brain) + qta-playwright (browser) | story-architect (tools) |
| **AI Suite Type** | Partner Expert | Partner Expert (same model) |
| **Runtime** | Python (core) + Node/Bun (playwright) | Python (FastMCP) |
| **Port** | 29108 (core), 29109 (playwright) | 29120 |
| **Key Difference** | Needs browser automation (Playwright MCP) | Needs codebase analysis + knowledge base |
| **Shared Pattern** | Natural language → structured output | Natural language → structured output |
