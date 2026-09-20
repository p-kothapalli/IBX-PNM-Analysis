# Design Document: User Story Architect Agent Upgrades (v1.5)

**Status:** Draft  
**Date:** 2026-03-29  
**Supersedes:** `User_Story_Architect_Agent_Approach.md` (v1.0)  
**Related:** `.cursor/skills/user-story-architect/SKILL.md`, `story-completeness-check.md`, `omnistudio-naming.md`

---

## 1. Executive Summary

The initial architecture for the User Story Architect Agent provides a strong foundation for generating implementation-ready requirements for Salesforce HLS/PNM projects using local file analysis and a question-first conversational flow.

To bridge the gap between a helpful drafting assistant and a fully integrated enterprise tool (similar to the QTA), this document outlines a set of strategic system upgrades. These upgrades focus on:

- **Robust state management** — Session-based artifact tracking so decision rationale is never lost
- **Live-org data validation** — SFDX integration to eliminate stale-data hallucinations
- **Standardized execution** — Prompt templates and workflow modes for predictable agent behavior
- **Downstream tool integration** — GUS/Jira handoff, QTA test bridge, and story dependency graphs
- **Deterministic validation** — Automated linting merged into the story-reviewer sub-agent

---

## 2. Proposed System Upgrades

### 2.1. Session-Based Artifact Management & Traceability

**Problem:** Currently, the agent outputs a single `.md` file. If the context window clears or the user steps away, the conversational history and intermediate decision-making logic (the "why" behind the story) are lost.

**Solution:** Implement a session-based directory structure that logs the entire lifecycle of a generated story.

**Implementation Details:**

1. Create a utility that initializes a unique `{SessionID}` (timestamp-based, e.g., `20260329_143022_ga_picklist`) upon execution.
2. Route all outputs to `<Workspace>/requirements/agent_sessions/{SessionID}/`.
3. Artifacts to generate per session:

| Artifact | Format | Purpose |
|----------|--------|---------|
| `final_story.md` | Markdown | The finalized user story |
| `interview_transcript.json` | JSON | Structured Q&A pairs between the SA and the agent (question, answer, phase, timestamp) |
| `component_delta.json` | JSON | Machine-readable mapping of impacted OmniStudio components for deployment tracking |
| `codebase_scan_results.json` | JSON | Grep/Glob results cached from the codebase analysis step |

**Phase:** Phase 2 (MCP)  
**Effort:** 2 days  
**Dependencies:** Filesystem access; no MCP required for basic implementation (mkdir + file writes)

**Recommendations (from review):**
- Use `interview_transcript.json` (structured) instead of `.txt` (raw text) for programmatic consumption
- Add a session cleanup policy: archive sessions older than 90 days to `agent_sessions/_archive/`
- `component_delta.json` is the highest-value artifact — define a schema so deployment pipelines can consume it
- Phase 1 fallback: if session infrastructure isn't built yet, continue writing a single `.md` to `requirements/`

**Example `component_delta.json` schema:**

```json
{
  "session_id": "20260329_143022_ga_picklist",
  "vertical": "PNM",
  "story_title": "Add Georgia State to Provider Credentialing Forms",
  "components": [
    {
      "name": "Address.PRM_State__c",
      "type": "Salesforce Picklist",
      "action": "ADD_VALUE",
      "detail": "Add Georgia (GA)",
      "impact": "HIGH"
    },
    {
      "name": "PRM_PractitionerParticipationForm_English",
      "type": "OmniScript",
      "action": "MODIFY_ELEMENT",
      "detail": "PractitionerState element — add GA to options",
      "impact": "HIGH"
    }
  ],
  "dependencies": [
    "GA_Internal_Credentialing_User_Stories.md"
  ]
}
```

---

### 2.2. Standardized Execution Prompts

**Problem:** Relying on generic natural language prompts (e.g., "I need a story about X") leads to unpredictable conversational flows and requires the agent to spend tokens figuring out the user's persona and goal.

**Solution:** Introduce standardized prompt templates as **optional accelerators** to immediately contextualize the agent's run state. Natural language prompts must still be accepted and mapped internally.

**Implementation Details:** Add prompt aliases to the `SKILL.md` file.

| Workflow | Prompt Template | Agent Mode |
|----------|----------------|------------|
| **New Feature** | `Architect Story: Capability <Name> for Vertical <Vertical>` | Full question flow (Phase 1–4) |
| **Refactor** | `Refactor Story: Component <OmniScript_Name> to implement <Requirement>` | Skip Phase 1, start at Phase 2 (component already known) |
| **Epic Breakdown** | `Generate Epics: Read <spec_file> and break down into stories for <Vertical>` | Bulk mode — decompose into N stories with cross-references |
| **Bug Fix** | `Fix Story: Defect <ID> in <Component> — current: <behavior>, expected: <behavior>` | Skip Phase 1–2, focus on Phase 3–4 |

**Smart Detection Rules:**

When the user types natural language instead of a template, map to the closest workflow:
- Contains "user story" or "story for" → **New Feature**
- Contains "refactor" or "change existing" → **Refactor**
- Contains "break down" or "epic" or "spec" → **Epic Breakdown**
- Contains "bug" or "defect" or "fix" → **Bug Fix**

**Phase:** Phase 1 (MVP) — add to SKILL.md  
**Effort:** 0.5 day  
**Dependencies:** None

**Recommendations (from review):**
- Templates are **shortcuts, not requirements** — natural language must always work
- `Generate Epics` requires PDF parsing — document this dependency (Cursor Read tool supports PDF)
- Add a `--dry-run` mode that shows which components would be analyzed without generating the full story

---

### 2.3. Live Org Metadata Validation (SFDX Integration)

**Problem:** The current design relies on parsing local `force-app/` JSON files. Local repositories often fall out of sync with the actual state of the Salesforce sandbox, leading the agent to generate technical specifications based on stale data.

**Solution:** Integrate the Salesforce CLI (SFDX) into the MCP Server to fetch real-time metadata, with graceful fallback to local files when no active session exists.

**Implementation Details:**

1. Add an MCP tool: `query_org_metadata(component_type, component_name, target_org)`.
2. This tool securely utilizes the user's active SFDX session to query the target org and retrieve the live JSON configuration of DataRaptors, Integration Procedures, or OmniScripts.
3. The agent compares local data with live data before writing the "Technical Section" of the user story.
4. Results are cached within the session to avoid redundant queries.

**Org Selection Flow:**

```
Agent: "I can validate components against a live Salesforce org.
        Do you have an active SFDX session?

        1. Yes — validate against my sandbox (default org)
        2. Yes — validate against a specific org alias: ________
        3. No — use local codebase only (force-app/)"
```

**Graceful Degradation:**

| Scenario | Behavior |
|----------|----------|
| Active SFDX session exists | Fetch live metadata; compare with local; flag drift |
| No SFDX session | Fall back to local `force-app/` files (current behavior) |
| SFDX query times out (>5s) | Use local files; warn user of potential staleness |
| Component exists locally but not in org | Flag as "potentially deleted or not yet deployed" |
| Component exists in org but not locally | Flag as "org-only — not in local repo" |

**Performance Considerations:**

- Cache all query results in `codebase_scan_results.json` (session artifact from 2.1)
- Batch queries where possible: `sf org list metadata --type OmniScript` retrieves all OmniScripts in one call
- Expected overhead: 3–8 seconds per batch query; 15–30 seconds for full component sweep

**Phase:** Phase 3 (Enterprise)  
**Effort:** 3 days  
**Dependencies:** SFDX CLI installed and authenticated; MCP server (Phase 2)

**Recommendations (from review):**
- Implement as **opt-in** ("Should I validate against the live org?") — not mandatory
- Add `--org` parameter to specify target org alias
- Clearly document which org type (sandbox vs. scratch vs. production) is appropriate for validation
- Address security: never log credentials or access tokens in session artifacts

---

### 2.4. Automated Story Linting (Integrated Validation)

**Problem:** LLMs occasionally hallucinate formatting or fail to adhere strictly to naming conventions (e.g., forgetting the `PRM_` prefix), requiring manual human review.

**Solution:** Integrate deterministic validation checks into the existing **story-reviewer sub-agent** to programmatically validate output before presenting it to the user.

> **Note:** The original design already includes `story-completeness-check.md` (rule), `omnistudio-naming.md` (rule), and a `story-reviewer` sub-agent. This upgrade **merges** linting capabilities into that existing infrastructure rather than creating a parallel validation path.

**Implementation Details:**

Validation checks to integrate into the story-reviewer sub-agent:

| Check | Type | What It Validates | Action on Failure |
|-------|------|-------------------|-------------------|
| **Gherkin Syntax** | Regex | AC sections follow `Given / When / Then` exactly | Auto-correct formatting; re-validate |
| **Naming Convention** | Lookup | All component names match vertical's convention registry (`omnistudio-naming.md`) | Flag non-conforming names; suggest corrections |
| **Section Completeness** | Structure | All required sections present (Persona, Story, Technical, AC, Questions) | List missing sections; kick back to agent |
| **Component Existence** | Codebase | Referenced components exist in `force-app/` (or live org if 2.3 is active) | Flag unverified components; add to Clarification Questions |
| **Cross-Story Conflict** | Search | No contradictions with existing stories in `requirements/` | List conflicting stories with file paths |

**Validation Flow:**

```
Agent generates story
  → story-reviewer sub-agent runs validation checks
    → All pass? → Present to user
    → Any fail? → Auto-correct where possible → Re-validate → Present with warnings
```

**Phase:** Phase 2 (MCP)  
**Effort:** 1.5 days  
**Dependencies:** Existing story-reviewer sub-agent; `omnistudio-naming.md` rule

**Recommendations (from review):**
- Do NOT create a separate `validate_story.py` Python script — this duplicates the existing rule infrastructure
- Keep deterministic checks (regex for Gherkin, string matching for naming) separate from LLM-based checks (cross-story conflict detection)
- Add a `--strict` mode that blocks story output until all checks pass (for CI/CD pipeline use)

---

### 2.5. Work Tracker Integration (GUS / Jira / Rally)

**Problem:** The workflow currently ends at the creation of a Markdown file, requiring the user to manually copy-paste the content into GUS, Jira, or Rally.

**Solution:** Build an opt-in API handoff mechanism to automate ticket creation.

**Implementation Details:**

1. Add a final step to the agent's conversation flow: *"The story is validated. Would you like me to create a work item?"*
2. Create an MCP tool `create_work_item(payload, target_system)` that parses the `.md` file into the target system's format.

**Field Mapping:**

| Story Section | GUS Field | Jira Field | Rally Field |
|--------------|-----------|------------|-------------|
| Persona | Team / Role | Labels / Tags | Owner |
| Story (As a / I want / So that) | Description | Description | Description |
| Why it matters | Details__c | Description (appended) | Notes |
| Priority (P0/P1/P2) | Priority | Priority | Priority |
| Acceptance Criteria | Acceptance_Criteria__c | AC custom field | Acceptance Criteria |
| OmniScript reference | Found_In_Build__c (or custom) | Component label | Feature tag |
| Clarification Questions | Description (appended) | Comment | Discussion |

**Target System Priority:**

| System | Priority | Rationale |
|--------|----------|-----------|
| **GUS** | **P0 — Build first** | This workspace already has `sf CLI` GUS skills; team uses GUS daily |
| Jira | P2 — Defer | Requires OAuth/API key setup; formatting differences (wiki syntax vs. markdown) |
| Rally | P2 — Defer | Niche usage; same formatting challenges as Jira |

**Phase:** Phase 3 (Enterprise) — GUS only; Jira/Rally deferred to Phase 4+  
**Effort:** 2 days (GUS); 3 days (Jira); 2 days (Rally)  
**Dependencies:** GUS: `sf data create record` CLI; Jira: REST API + OAuth token; Rally: Rally REST API

**Recommendations (from review):**
- Start with **GUS** since the workspace already has `aisuite_sfcli_gus` skill — reuse existing auth
- For Jira, consider a lightweight "copy to clipboard in Jira format" option before building full API integration
- Use `sf data create record -s ADM_Work__c` for GUS ticket creation via existing CLI patterns

---

### 2.6. System Permissions & OS Setup

**Problem:** Advanced MCP tools (like running SFDX commands or creating folders) require elevated OS permissions that might silently block the agent if not configured.

**Solution:** Standardize the prerequisite setup instructions to match QTA standards.

**Implementation Details:**

Update the `README.md` to include a Prerequisites section:

```markdown
## Prerequisites

### macOS Permissions (Required for MCP tools)

1. Open **System Settings → Privacy & Security → Accessibility**
2. Add your terminal application (Terminal.app, iTerm2, or Cursor)
3. Open **System Settings → Privacy & Security → Automation**
4. Grant "System Events" access to your terminal application

### SFDX CLI (Required for Live Org Validation — Phase 3)

1. Install: `npm install -g @salesforce/cli`
2. Authenticate: `sf org login web --alias my-sandbox`
3. Verify: `sf org display --target-org my-sandbox`
```

**Phase:** Phase 2 (include in MCP server README)  
**Effort:** 0.5 day  
**Dependencies:** None

**Note:** This is documentation/setup guidance, not an architectural upgrade. Included here for completeness since it's a prerequisite for upgrades 2.3 and 2.4.

---

## 3. New Upgrades (Recommended Additions)

These upgrades were identified during review of the original architecture and are not in the initial v1.5 proposal.

### 3.1. Multi-Story Dependency Graph

**Problem:** The original design mentions "Cross-Story Dependency Detection" (C10) but neither the v1.0 architecture nor v1.5 upgrades propose an implementation. When generating GA stories, 6 existing GA stories + 14 other requirement files had implicit dependencies that weren't tracked.

**Solution:** Generate a `story_dependency_graph.json` artifact that maps which stories block, depend on, or conflict with each other.

**Implementation Details:**

- After story generation, scan `requirements/` for all stories that share components, objects, or flows
- Build a directed graph: Story A → blocks → Story B; Story C → depends on → Story D
- Store as session artifact and optionally visualize via the canvas skill

**Example output:**

```json
{
  "nodes": [
    {"id": "GA_Picklist_Expansion", "file": "GA_State_County_Picklist_Expansion_User_Story.md", "priority": "P1"},
    {"id": "GA_Quick_Links", "file": "GA_Internal_Credentialing_User_Stories.md#US4", "priority": "P1"},
    {"id": "GA_Form_Source", "file": "GA_Internal_Credentialing_User_Stories.md#US5", "priority": "P0"}
  ],
  "edges": [
    {"from": "GA_Picklist_Expansion", "to": "GA_Quick_Links", "type": "blocks"},
    {"from": "GA_Picklist_Expansion", "to": "GA_Form_Source", "type": "blocks"}
  ]
}
```

**Phase:** Phase 2 (MCP)  
**Effort:** 1.5 days

---

### 3.2. Story Versioning & Diff

**Problem:** When a story is updated (priority changed, new AC added, scope expanded), the `.md` file is overwritten with no history. Teammates can't see what changed or why.

**Solution:** Before overwriting a story, generate a structured diff summary and maintain a revision log at the bottom of each story file.

**Implementation Details:**

- Before writing `final_story.md`, check if a previous version exists
- If yes, compute a section-level diff (not line-level — sections are more meaningful)
- Append a `## Revision History` section to the story

**Example:**

```markdown
## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.1 | 2026-03-30 | Agent | Added Scenario 11 (Ancillary form edge case); upgraded priority from P1 to P0 |
| 1.0 | 2026-03-29 | Agent | Initial story generation |
```

**Phase:** Phase 2 (MCP)  
**Effort:** 1 day

---

### 3.3. Effort Estimation

**Problem:** The original design mentions "effort estimates" in capability C7 (Implementation Plan) but neither SKILL.md nor the output template implements this. Developers and PMs consistently need story points or t-shirt sizing.

**Solution:** Add an `## Estimated Effort` section to the user story output template with component-level effort breakdowns.

**Implementation Details:**

Add to SKILL.md output format:

```markdown
## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| Address.PRM_State__c | Picklist value add | S (< 1 hr) | Admin change; no code |
| PRM_PractitionerParticipationForm_English | OmniScript element edit | M (2–4 hrs) | Modify PractitionerState options |
| PRMExtractCountyByState | New DataRaptor | L (4–8 hrs) | Build Extract + filter logic |
| PRM_AncillaryProviderUtilsService | Apex class edit | XL (1–2 days) | Logic change + unit tests |

**Total Estimated Effort:** [Sum] story points / [T-shirt size]
```

**Effort Sizing Guide:**

| Size | Hours | Description |
|------|-------|-------------|
| **S** | < 1 hr | Config change, picklist update, metadata record |
| **M** | 2–4 hrs | OmniScript element edit, DataRaptor field add, simple IP change |
| **L** | 4–8 hrs | New DataRaptor, new IP step, OmniScript step redesign |
| **XL** | 1–2 days | New Apex class, complex IP chain, new OmniScript flow |
| **XXL** | 3+ days | Cross-flow redesign, new object model, multi-component integration |

**Phase:** Phase 1 (MVP) — add to SKILL.md output template  
**Effort:** 0.5 day

---

### 3.4. QTA Test Bridge

**Problem:** The workspace has a QTA (Quality Test Agent) for browser automation testing. The user stories generate acceptance criteria in Gherkin format — this is exactly what QTA needs as input. There is no bridge between the two.

**Solution:** Add an optional "Generate QTA Test Prompt" step that converts acceptance criteria into QTA-compatible test prompts.

**Implementation Details:**

After story validation, offer:

```
Agent: "This story has 10 acceptance criteria in Gherkin format.
        Would you like me to generate QTA test prompts for browser automation?"
```

**Mapping:**

| Story Section | QTA Input |
|--------------|-----------|
| Given (precondition) | Navigation steps + setup |
| When (action) | User interaction steps |
| Then (expected result) | Assertion checks |
| OmniScript name | Target URL / flow identifier |

**Example output:**

```
QTA Test Prompt: "Navigate to PRM_PractitionerParticipationForm_English.
Open the PractitionerState dropdown in the AddLicenseBlock step.
Verify that Georgia (GA) appears as a selectable option.
Select Georgia. Verify the county dropdown appears with options:
Fulton, Cobb, Clayton, DeKalb, Gwinnett."
```

**Phase:** Phase 3 (Enterprise)  
**Effort:** 1.5 days  
**Dependencies:** QTA MCP server (`user-qta-core`)

---

### 3.5. Bulk Story Mode (Epic Decomposition)

**Problem:** Complex scope documents (like `GA_Internal_Credentialing_Scope_Implementation_Plan.md`) require 6+ user stories. Currently, the agent generates one story at a time in a single conversation.

**Solution:** Given a scope document or feature spec, auto-decompose into N stories and generate them in sequence with cross-references and a dependency graph.

**Implementation Details:**

1. Agent reads the scope document
2. Identifies logical story boundaries (per-flow, per-component, per-persona)
3. Proposes a story decomposition plan for user approval
4. Generates each story sequentially, adding cross-references between them
5. Produces a summary `epic_overview.md` with dependency graph

**Trigger:** `Generate Epics: Read <file> and break down into stories for <Vertical>`

**Phase:** Phase 2 (MCP)  
**Effort:** 2 days

---

## 4. Consolidated Implementation Roadmap (v1.5)

This roadmap merges the original 4-phase plan with the v1.5 upgrades and new recommendations.

### Phase 1: Local Skill + MVP (Weeks 1–2)

**Goal:** Working agent in Cursor that asks questions and generates implementation-ready user stories using built-in tools only.

| Task | Description | Source | Effort |
|------|-------------|--------|--------|
| 1.1 | Create `SKILL.md` with vertical selection, question flow, and output format | Original | 2 days |
| 1.2 | Create `references/` with OmniStudio component reference and PNM object model | Original | 1 day |
| 1.3 | Create `references/story-examples.md` with 3 exemplar stories | Original | 0.5 day |
| 1.4 | Create rules: `story-completeness-check.md`, `omnistudio-naming.md` | Original | 0.5 day |
| 1.5 | **Add standardized execution prompts to SKILL.md** | **Upgrade 2.2** | **0.5 day** |
| 1.6 | **Add effort estimation section to output template** | **New 3.3** | **0.5 day** |
| 1.7 | Test with 5 real requirements from the project | Original | 1 day |
| 1.8 | Iterate on SKILL.md based on output quality | Original | 2 days |

**Deliverable:** `.cursor/skills/user-story-architect/SKILL.md` + `references/` + rules  
**Total Effort:** ~8.5 days

---

### Phase 2: MCP Server + Session Management (Weeks 3–5)

**Goal:** Add MCP tools for codebase analysis, impact detection, session artifacts, story linting, and bulk story mode.

| Task | Description | Source | Effort |
|------|-------------|--------|--------|
| 2.1 | Create Python MCP server with FastMCP | Original | 1 day |
| 2.2 | Implement `analyze_omniscript` tool (parse element JSONs) | Original | 2 days |
| 2.3 | Implement `find_impacted_components` tool (cross-reference search) | Original | 2 days |
| 2.4 | Implement `search_existing_stories` tool | Original | 0.5 day |
| 2.5 | Implement `select_vertical` with config loading | Original | 1 day |
| 2.6 | **Session-based artifact management** (session dirs, `component_delta.json`, `interview_transcript.json`) | **Upgrade 2.1** | **2 days** |
| 2.7 | **Integrate deterministic linting into story-reviewer sub-agent** (Gherkin regex, naming validation) | **Upgrade 2.4** | **1.5 days** |
| 2.8 | **Story dependency graph** (`story_dependency_graph.json`) | **New 3.1** | **1.5 days** |
| 2.9 | **Story versioning & diff** (revision history, section-level diffs) | **New 3.2** | **1 day** |
| 2.10 | **Bulk story mode** (epic decomposition from scope docs) | **New 3.5** | **2 days** |
| 2.11 | Integration testing with real OmniScript metadata | Original | 1 day |

**Deliverable:** MCP server on port 29120 with session artifacts, linting, dependency graphs, bulk mode  
**Total Effort:** ~15.5 days

---

### Phase 3: AI Expert Suite + Live Org + Integrations (Weeks 6–8)

**Goal:** Package as Expert, add SFDX live validation, GUS integration, and QTA test bridge.

| Task | Description | Source | Effort |
|------|-------------|--------|--------|
| 3.1 | Create Git repo on git.soma.salesforce.com | Original | 0.5 day |
| 3.2 | Structure as Expert (skills/, rules/, agents/, mcp server) | Original | 1 day |
| 3.3 | Write README with prerequisites and OS setup instructions | Original + **Upgrade 2.6** | 0.5 day |
| 3.4 | Submit PR to expert-registry | Original | 0.5 day |
| 3.5 | **SFDX live org metadata validation** (opt-in, graceful fallback, caching) | **Upgrade 2.3** | **3 days** |
| 3.6 | **GUS work item creation** (via `sf data create record`) | **Upgrade 2.5** | **2 days** |
| 3.7 | **QTA test bridge** (AC → QTA test prompts) | **New 3.4** | **1.5 days** |
| 3.8 | Team testing and feedback | Original | 2 days |

**Deliverable:** Expert in AI Suite UI; SFDX validation; GUS integration; QTA bridge  
**Total Effort:** ~11 days

---

### Phase 4: RAG + Multi-Vertical + External Integrations (Weeks 9–12)

**Goal:** Add vector search, additional verticals, story-reviewer sub-agent, and Jira/Rally integration.

| Task | Description | Source | Effort |
|------|-------------|--------|--------|
| 4.1 | Index existing stories and OmniScript metadata into vector store | Original | 2 days |
| 4.2 | Add Insurance and FSC vertical configs | Original | 2 days |
| 4.3 | Build story-reviewer sub-agent (LLM-based review on top of deterministic linting) | Original | 2 days |
| 4.4 | Add implementation plan generation | Original | 2 days |
| 4.5 | Integration with Agent Exchange for discovery | Original | 1 day |
| 4.6 | Jira REST API integration (if needed) | Upgrade 2.5 | 3 days |
| 4.7 | Rally integration (if needed) | Upgrade 2.5 | 2 days |

**Deliverable:** Full-featured agent with RAG, multi-vertical, and external integrations  
**Total Effort:** ~14 days

---

## 5. Upgrade Priority Matrix

| Upgrade | Impact on Story Quality | Implementation Effort | Phase | Priority |
|---------|------------------------|----------------------|-------|----------|
| **2.3 SFDX Live Org Validation** | Very High — eliminates stale-data hallucinations | 3 days | Phase 3 | **P0** |
| **2.1 Session Artifacts** | High — preserves decision rationale; enables deployment tracking | 2 days | Phase 2 | **P0** |
| **2.2 Standardized Prompts** | Medium — reduces token waste; improves predictability | 0.5 day | Phase 1 | **P1** |
| **3.3 Effort Estimation** | Medium — fills gap in developer/PM handoff | 0.5 day | Phase 1 | **P1** |
| **2.4 Story Linting** | Medium — catches formatting issues deterministically | 1.5 days | Phase 2 | **P1** |
| **3.1 Dependency Graph** | Medium — tracks cross-story relationships | 1.5 days | Phase 2 | **P1** |
| **3.4 QTA Test Bridge** | Medium — closes requirements→testing loop | 1.5 days | Phase 3 | **P1** |
| **3.5 Bulk Story Mode** | Medium — saves time on large scope documents | 2 days | Phase 2 | **P1** |
| **3.2 Story Versioning** | Low-Medium — nice audit trail but not critical | 1 day | Phase 2 | **P2** |
| **2.5 GUS Integration** | Low-Medium — saves manual copy-paste | 2 days | Phase 3 | **P2** |
| **2.6 OS Setup Docs** | Low — documentation only | 0.5 day | Phase 2 | **P2** |
| **2.5 Jira/Rally** | Low — team uses GUS, not Jira | 5 days | Phase 4 | **P3** |

---

## 6. Risk & Mitigation (Updated)

| # | Risk | Impact | Mitigation |
|---|------|--------|-----------|
| R1 | LLM generates incorrect OmniScript element names | Developer builds wrong thing | `analyze_omniscript` validates against codebase; SFDX validates against live org (2.3); story-reviewer cross-checks (2.4) |
| R2 | Agent doesn't ask enough questions | Generic, unusable stories | SKILL.md enforces minimum 5 questions; completeness rule catches missing sections; standardized prompts (2.2) reduce ambiguity |
| R3 | Local codebase is out of sync with live org | Technical section references stale components | **SFDX integration (2.3)** — opt-in live validation with graceful fallback |
| R4 | Session artifacts fill disk over time | Storage bloat | Session cleanup policy (archive after 90 days); `.gitignore` for `agent_sessions/` |
| R5 | SFDX auth expires mid-session | Agent can't validate live org | Graceful fallback to local files; warn user of potential staleness |
| R6 | Effort estimates are inaccurate | PM plans around wrong numbers | Clearly label as "AI-estimated — validate with team"; provide range (not point estimate) |
| R7 | QTA test prompts don't match actual UI state | Tests fail on execution | QTA bridge generates prompts for human review before execution; not auto-run |
| R8 | Bulk story mode produces shallow stories | Quantity over quality | Limit to max 10 stories per epic; require user confirmation of decomposition plan before generation |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.5 | 2026-03-29 | Agent | Reformatted from raw text; added recommendations from review; added 5 new upgrades (3.1–3.5); created consolidated 4-phase roadmap; added priority matrix and updated risk table |
| 1.5-draft | 2026-03-29 | User | Initial unformatted draft with 6 proposed upgrades |
| 1.0 | — | User | Original architecture: `User_Story_Architect_Agent_Approach.md` |

---

*Source: User Story Architect Agent Approach v1.0, GA story generation session (2026-03-29), QTA architecture comparison*
