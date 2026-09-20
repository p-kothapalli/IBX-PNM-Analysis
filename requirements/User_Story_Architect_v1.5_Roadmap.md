# User Story Architect — Consolidated v1.5 Roadmap

**Date:** 2026-03-29  
**Status:** Active  
**Source Documents:**
- `User_Story_Architect_Agent_Approach.md` (v1.0 — original architecture)
- `userStoryAgentUpgrades.md` (v1.5 — upgrade proposals + review recommendations)
- `.cursor/skills/user-story-architect/SKILL.md` (v1.5 — updated skill)

---

## Executive Summary

This roadmap merges the original 4-phase implementation plan with the v1.5 system
upgrades and 5 newly recommended additions. It covers 12 weeks of incremental
delivery from a local Cursor skill (Phase 1) to a fully integrated enterprise
agent with live org validation, GUS integration, QTA test bridge, and multi-vertical
support (Phase 4).

### What Changed from v1.0 to v1.5

| Area | v1.0 (Original) | v1.5 (Upgraded) |
|------|-----------------|-----------------|
| **Workflow Modes** | Single mode: question-first | 4 modes: New Feature, Refactor, Epic Breakdown, Bug Fix |
| **Output Template** | Story + Technical + AC + Questions + Impact | + **Estimated Effort** (S/M/L/XL/XXL sizing) |
| **Session Tracking** | Single `.md` file output | Session directory with `final_story.md`, `interview_transcript.json`, `component_delta.json` |
| **Validation** | Rule-based (completeness + naming) | Rule-based + deterministic linting (Gherkin regex, convention matching) integrated into story-reviewer |
| **Org Data** | Local `force-app/` only | Opt-in SFDX live org validation with graceful fallback |
| **Downstream** | None (story ends at `.md` file) | GUS work item creation, QTA test bridge, story dependency graph |
| **Bulk Mode** | One story per conversation | Epic decomposition: scope doc → N stories with cross-references |
| **Versioning** | Overwrite on update | Revision history section with section-level diffs |

---

## Phase 1: Local Skill + MVP (Weeks 1–2)

**Goal:** Working agent in Cursor that asks questions and generates implementation-ready user stories using built-in tools only. No MCP server required.

**Theme:** Get the core right — question flow, output format, codebase scanning.

| # | Task | Source | Effort | Status |
|---|------|--------|--------|--------|
| 1.1 | Create `SKILL.md` with vertical selection, question flow, output format | Original | 2 days | **Done** |
| 1.2 | Create `references/` with OmniStudio component reference and PNM object model | Original | 1 day | **Done** |
| 1.3 | Create `references/story-examples.md` with 3 exemplar stories | Original | 0.5 day | **Done** |
| 1.4 | Create rules: `story-completeness-check.md`, `omnistudio-naming.md` | Original | 0.5 day | **Done** |
| 1.5 | Add standardized execution prompts (4 workflow modes) to SKILL.md | Upgrade 2.2 | 0.5 day | **Done** |
| 1.6 | Add Estimated Effort section + sizing guide to output template | New 3.3 | 0.5 day | **Done** |
| 1.7 | Add QTA test bridge offer + GUS work item offer + Lucid diagram generation to post-gen steps | New 3.4 / 2.5 | 0.5 day | **Done** |
| 1.8 | Test with 5 real requirements from the project | Original | 1 day | **Done** |
| 1.9 | Iterate on SKILL.md based on output quality | Original | 2 days | **Done** |

**Deliverables:**
- `.cursor/skills/user-story-architect/SKILL.md` (v1.5)
- `.cursor/rules/story-completeness-check.md`
- `.cursor/rules/omnistudio-naming.md`
- `references/` directory (OmniStudio components, PNM object model, story examples)

**Total Effort:** ~8.5 days

**Exit Criteria:**
- [x] Agent correctly detects all 4 workflow modes from natural language
- [x] Agent asks 5+ questions before generating any story
- [x] Generated stories include all required sections + Estimated Effort
- [x] Naming conventions match PNM vertical (PRM_ prefix verified)
- [x] 5+ test stories generated and reviewed for quality (GA Picklist, Life Sciences Visit Mgmt x12, Broker Portal, etc.)

---

## Phase 2: MCP Server + Session Management (Weeks 3–5)

**Goal:** Add MCP tools for codebase analysis, impact detection, session artifacts, story linting, and bulk story mode.

**Theme:** Machine-readable artifacts and automated validation.

| # | Task | Source | Effort | Status |
|---|------|--------|--------|--------|
| 2.1 | Create Python MCP server with FastMCP (stdio + HTTP port 29120) | Original | 1 day | **Done** |
| 2.2 | Implement `analyze_omniscript` tool (parse element JSONs) | Original | 2 days | **Done** |
| 2.3 | Implement `find_impacted_components` tool (cross-reference search) | Original | 2 days | **Done** |
| 2.4 | Implement `search_existing_stories` tool | Original | 0.5 day | **Done** |
| 2.5 | Implement `select_vertical` with YAML config loading (PNM, HLS, Insurance, FSC) | Original | 1 day | **Done** |
| 2.6 | Session-based artifact management — session dirs, `component_delta.json`, `interview_transcript.json`, `codebase_scan_results.json` | Upgrade 2.1 | 2 days | **Done** |
| 2.7 | Integrate deterministic linting — Gherkin regex, naming convention validation, section checks, effort disclaimer | Upgrade 2.4 | 1.5 days | **Done** |
| 2.8 | Story dependency graph — `story_dependency_graph.json` with nodes/edges + shared component detection | New 3.1 | 1.5 days | **Done** |
| 2.9 | Story versioning & diff — revision history, unified diffs, hash-based versions | New 3.2 | 1 day | **Done** |
| 2.10 | Bulk story mode — `decompose_scope_document` + `generate_bulk_story_skeleton` with cross-references | New 3.5 | 2 days | **Done** |
| 2.11 | System permissions documentation in MCP server README | Upgrade 2.6 | 0.5 day | **Done** |
| 2.12 | Integration testing with real workspace data (6 tests, all passing) | Original | 1 day | **Done** |

**Deliverables:**
- MCP server running locally on port 29120
- Session artifacts: `requirements/agent_sessions/{SessionID}/`
- `component_delta.json` schema for deployment pipeline consumption
- `story_dependency_graph.json` for cross-story tracking
- Deterministic linting integrated into story-reviewer sub-agent
- Bulk story mode (epic decomposition)

**Total Effort:** ~16 days

**Exit Criteria:**
- [x] MCP server starts and all 15 tools respond correctly
- [x] Session artifacts generated for every story run (4 files per session)
- [x] `component_delta.json` is valid JSON matching defined schema
- [x] Story linter catches Gherkin format violations and naming convention breaches (11 checks)
- [x] Dependency graph correctly identifies blocking/blocked + shared-component relationships
- [x] Bulk mode decomposes a scope doc into stories with cross-references (max 10)
- [x] Story versioning tracks revision history with unified diffs on updates

---

## Phase 3: AI Expert Suite + Live Org + Integrations (Weeks 6–8)

**Goal:** Package as Expert for team-wide distribution. Add SFDX live validation, GUS integration, and QTA test bridge.

**Theme:** Enterprise-grade validation and downstream integration.

| # | Task | Source | Effort | Status |
|---|------|--------|--------|--------|
| 3.1 | Create Git repo on git.soma.salesforce.com | Original | 0.5 day | Pending |
| 3.2 | Structure as Expert (skills/, rules/, agents/, MCP server) | Original | 1 day | Pending |
| 3.3 | Write README with prerequisites, OS setup, SFDX auth instructions | Original + Upgrade 2.6 | 0.5 day | Pending |
| 3.4 | Submit PR to expert-registry (`registry.yaml`) | Original | 0.5 day | Pending |
| 3.5 | SFDX live org metadata validation — `query_org_metadata` MCP tool, org selection flow, graceful fallback, session caching | Upgrade 2.3 | 3 days | Pending |
| 3.6 | GUS work item creation — `create_work_item` via `sf data create record -s ADM_Work__c`, field mapping | Upgrade 2.5 | 2 days | Pending |
| 3.7 | QTA test bridge — AC → QTA test prompts, one prompt per criterion, `qta_test_prompts.md` output | New 3.4 | 1.5 days | Pending |
| 3.8 | Team testing and feedback | Original | 2 days | Pending |

**Deliverables:**
- Expert available in AI Suite UI for the team
- SFDX live org validation (opt-in, graceful fallback)
- GUS work item creation from generated stories
- QTA test prompt generation from acceptance criteria
- README with full setup instructions

**Total Effort:** ~11 days

**Exit Criteria:**
- [ ] Expert registered in AI Suite and accessible by team
- [ ] SFDX validation works with active session; gracefully falls back without one
- [ ] Local vs. live org drift flagged in story output
- [ ] GUS work item created successfully with correct field mapping
- [ ] QTA test prompts generated for all AC scenarios
- [ ] Team feedback collected; top 3 issues addressed

---

## Phase 4: RAG + Multi-Vertical + External Integrations (Weeks 9–12)

**Goal:** Add vector search, additional verticals, story-reviewer sub-agent (LLM-based), and Jira/Rally integration.

**Theme:** Scale and intelligence.

| # | Task | Source | Effort | Status |
|---|------|--------|--------|--------|
| 4.1 | Index existing stories and OmniScript metadata into vector store | Original | 2 days | Pending |
| 4.2 | Add Insurance and FSC vertical configs (YAML + reference docs) | Original | 2 days | Pending |
| 4.3 | Build story-reviewer sub-agent (LLM-based review on top of deterministic linting) | Original | 2 days | Pending |
| 4.4 | Add implementation plan generation capability | Original | 2 days | Pending |
| 4.5 | Integration with Agent Exchange for discovery | Original | 1 day | Pending |
| 4.6 | Jira REST API integration (if team needs it) | Upgrade 2.5 | 3 days | Pending |
| 4.7 | Rally integration (if team needs it) | Upgrade 2.5 | 2 days | Pending |

**Deliverables:**
- RAG-powered story search and context retrieval
- Insurance + FSC vertical support
- Story-reviewer sub-agent with LLM-based technical accuracy checking
- Implementation plan generation
- Jira/Rally integration (if needed)

**Total Effort:** ~14 days

**Exit Criteria:**
- [ ] RAG search returns relevant stories for natural language queries
- [ ] Insurance vertical generates stories with correct naming conventions
- [ ] Story-reviewer catches technical inaccuracies LLM-based checks can find
- [ ] Implementation plan generated with phases, dependencies, and effort
- [ ] Agent discoverable in Agent Exchange

---

## Timeline Summary

```
Week  1  2  3  4  5  6  7  8  9  10  11  12
      ├──────┤                                 Phase 1: Local Skill + MVP
               ├────────────┤                  Phase 2: MCP + Session + Linting
                              ├──────────┤     Phase 3: Expert Suite + SFDX + GUS
                                           ├──────────────┤  Phase 4: RAG + Multi-Vertical
```

| Phase | Weeks | Total Effort | Key Deliverable |
|-------|-------|-------------|-----------------|
| Phase 1 | 1–2 | 8.5 days | Working agent in Cursor |
| Phase 2 | 3–5 | 16 days | MCP server + session artifacts + bulk mode |
| Phase 3 | 6–8 | 11 days | Expert Suite + SFDX + GUS + QTA bridge |
| Phase 4 | 9–12 | 14 days | RAG + multi-vertical + Jira/Rally |
| **Total** | **1–12** | **~49.5 days** | **Full-featured enterprise agent** |

---

## Priority Matrix (What to Build First)

| Priority | Upgrade | Phase | Impact | Effort |
|----------|---------|-------|--------|--------|
| **P0** | SFDX Live Org Validation | 3 | Eliminates stale-data hallucinations | 3 days |
| **P0** | Session Artifacts + `component_delta.json` | 2 | Preserves decision rationale; enables deployment tracking | 2 days |
| **P1** | Standardized Execution Prompts | 1 | Reduces token waste; predictable agent behavior | 0.5 day |
| **P1** | Effort Estimation in output | 1 | Fills gap in developer/PM handoff | 0.5 day |
| **P1** | Story Linting (integrated) | 2 | Catches format/naming issues deterministically | 1.5 days |
| **P1** | Story Dependency Graph | 2 | Tracks cross-story relationships | 1.5 days |
| **P1** | QTA Test Bridge | 3 | Closes requirements → testing loop | 1.5 days |
| **P1** | Bulk Story Mode | 2 | Saves hours on large scope documents | 2 days |
| **P2** | Story Versioning & Diff | 2 | Audit trail for story changes | 1 day |
| **P2** | GUS Work Item Creation | 3 | Saves manual copy-paste | 2 days |
| **P2** | OS Setup Documentation | 2 | Prevents silent MCP failures | 0.5 day |
| **P3** | Jira/Rally Integration | 4 | Team uses GUS, not Jira — low urgency | 5 days |

---

## Risk Register (v1.5)

| # | Risk | Likelihood | Impact | Mitigation | Phase |
|---|------|-----------|--------|-----------|-------|
| R1 | LLM generates incorrect component names | Medium | High | `analyze_omniscript` validates against codebase; SFDX validates against live org; story-reviewer cross-checks | 2, 3 |
| R2 | Agent asks too few questions, produces generic stories | Low | High | SKILL.md enforces minimum 5 questions; workflow detection adapts question flow; completeness rule | 1 |
| R3 | Local codebase out of sync with live org | High | High | SFDX integration (opt-in) with graceful fallback to local files | 3 |
| R4 | Session artifacts fill disk over time | Medium | Low | Cleanup policy: archive sessions > 90 days; `.gitignore` for `agent_sessions/` | 2 |
| R5 | SFDX auth expires mid-session | Medium | Medium | Graceful fallback to local files; warn user of potential staleness | 3 |
| R6 | Effort estimates inaccurate | High | Medium | Label as "AI-estimated — validate with team"; provide ranges not point estimates | 1 |
| R7 | QTA test prompts don't match actual UI state | Medium | Medium | Generate for human review before execution; not auto-run | 3 |
| R8 | Bulk mode produces shallow stories | Medium | High | Limit max 10 stories per epic; require user approval of decomposition plan | 2 |
| R9 | SKILL.md exceeds context window | Low | High | Use `references/` for large docs (loaded on demand); keep SKILL.md < 12K tokens | 1 |
| R10 | Team adoption low | Medium | High | Start with Phase 1 (zero setup); gather feedback before Phase 2 investment | 1 |

---

## Current Progress Tracker

### Phase 1 Status — ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| SKILL.md created (v1.5) | **Done** | Updated with workflow modes, effort estimation, QTA bridge, Lucid diagrams, post-gen offers |
| `story-completeness-check.md` rule | **Done** | Validates required sections |
| `omnistudio-naming.md` rule | **Done** | Enforces PRM_ prefix |
| Standardized execution prompts | **Done** | 4 workflow modes + smart detection |
| Effort estimation guide | **Done** | S/M/L/XL/XXL sizing in SKILL.md |
| QTA bridge + GUS offer + Lucid | **Done** | Post-generation steps in SKILL.md |
| `references/` directory | **Done** | OmniStudio components (144 lines), PNM object model (190 lines), story examples (195 lines) |
| Test with 5+ real requirements | **Done** | GA picklist, Life Sciences Visit Mgmt (12 stories), Broker Portal, multiple PNM stories |
| Iterate on quality | **Done** | SKILL.md updated with Lucid diagram integration, HLS vertical context |

### Phase 2 Status — ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| MCP server (FastMCP, stdio + HTTP) | **Done** | `mcp_server/server.py` — 15 tools registered, all passing |
| `analyze_omniscript` tool | **Done** | Parses element JSONs, steps, conditions, data sources |
| `find_impacted_components` tool | **Done** | Cross-reference search across force-app/ and requirements/ |
| `search_existing_stories` tool | **Done** | Keyword search in requirements/*.md |
| `select_vertical` with YAML configs | **Done** | PNM, HLS, Insurance, FSC configs in `mcp_server/verticals/` |
| Session artifact management | **Done** | 6 session tools: create, save Q&A, save delta, save scan, finalize |
| Deterministic linting | **Done** | Gherkin, sections, persona, story format, effort disclaimer (11 checks) |
| Story dependency graph | **Done** | Blocking + shared-component edge detection; JSON schema |
| Story versioning & diff | **Done** | Unified diffs, hash-based version IDs, revision history table |
| Bulk story mode | **Done** | `decompose_scope_document` + `generate_bulk_story_skeleton` |
| README + permissions docs | **Done** | `mcp_server/README.md` with full tool reference |
| Integration testing | **Done** | 6 tests against real workspace data, all passing |

### Artifacts Generated So Far

| Artifact | Path | Date |
|----------|------|------|
| User Story (GA Picklist Expansion) | `requirements/GA_State_County_Picklist_Expansion_User_Story.md` | 2026-03-29 |
| Upgrade Design Doc (v1.5) | `requirements/userStoryAgentUpgrades.md` | 2026-03-29 |
| SKILL.md (v1.5) | `.cursor/skills/user-story-architect/SKILL.md` | 2026-03-29 |
| AGENTS.md | `.cursor/AGENTS.md` | 2026-03-29 |
| This Roadmap | `requirements/User_Story_Architect_v1.5_Roadmap.md` | 2026-03-29 |
| Life Sciences Visit Mgmt (12 stories) | `requirements/LifeSciences_VisitManagement_DetailedUserStories.md` | 2026-03-30 |
| Life Sciences Business User Guide | `requirements/LifeSciences_VisitManagement_BusinessUserGuide.md` | 2026-03-30 |
| MCP Server (Phase II) | `mcp_server/server.py` (15 tools) | 2026-03-31 |
| Vertical Configs (4) | `mcp_server/verticals/{pnm,hls,insurance,fsc}.yaml` | 2026-03-31 |
| JSON Schemas (2) | `mcp_server/schemas/{component_delta,story_dependency_graph}.json` | 2026-03-31 |
| MCP Server README | `mcp_server/README.md` | 2026-03-31 |
| Cursor MCP Config (updated) | `.cursor/mcp.json` (added user-story-architect server) | 2026-03-31 |

---

## Resources & References

### Internal Resources

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

### Salesforce Health Cloud & PNM Data Models

| Resource | URL | Purpose |
|----------|-----|---------|
| **Provider Data Model (PNM)** | [Trailhead](https://trailhead.salesforce.com/content/learn/modules/health-cloud-data-models/learn-about-the-provider-data-model) | Healthcare Provider, Healthcare Facility, Healthcare Practitioner Facility, Healthcare Payer Network, Healthcare Provider NPI, Business License, Board Certification |
| **Household Data Model (HLS)** | [Trailhead](https://trailhead.salesforce.com/content/learn/modules/health-cloud-data-models/learn-about-the-household-data-model) | Families, relationships, household members, contacts |
| **Clinical Data Model (HLS)** | [Trailhead](https://trailhead.salesforce.com/content/learn/modules/health-cloud-data-models/examine-the-clinical-data-model) | Conditions, medications, observations, care teams, care providers, clinical documentation |
| **Care Program Data Model (HLS)** | [Trailhead](https://trailhead.salesforce.com/content/learn/modules/health-cloud-data-models/get-to-know-the-care-program-data-model) | Programs, enrollments, care goals, care milestones, outcomes |
| **Health Cloud Data Models (All)** | [Trailhead](https://trailhead.salesforce.com/content/learn/modules/health-cloud-data-models) | Full curriculum: Household, Clinical, Insurance/Claims, Care Program, Social Determinants, Provider, Utilization Management |
| **Health Cloud Object Reference** | [Developer Docs](https://developer.salesforce.com/docs/atlas.en-us.health_cloud_object_reference.meta/health_cloud_object_reference/sforce_api_objects.htm) | Complete API reference for all Health Cloud objects, fields, relationships, and methods |
| **Health Cloud Developer Guide** | [Developer Docs](https://developer.salesforce.com/docs/atlas.en-us.health_cloud_dev_guide.meta/health_cloud_dev_guide/health_cloud_dev_guide.htm) | Comprehensive guide covering all data models, patterns, integrations, and best practices |
| **Salesforce Life Sciences Librarian** | [NotebookLM](https://notebooklm.google.com/notebook/55caac49-5167-4731-bc4f-e1369a88030e) | Shared knowledge base with HLS best practices, data models, workflows, and implementation patterns (internal) |
| **OmniStudio Component Reference** | [Salesforce Help](https://help.salesforce.com/s/articleView?id=xcloud.os_omnistudio_standard.htm&type=5) | Standard OmniStudio components (OmniScript, DataRaptor, Integration Procedure, FlexCard, DataMapper, Decision Matrix) |

---

## Decision Log

| # | Decision | Rationale | Date |
|---|----------|-----------|------|
| D1 | Merge story linting into existing story-reviewer sub-agent instead of creating separate `validate_story.py` | Avoids duplicate validation paths; reduces deployment complexity; existing rules already handle completeness | 2026-03-29 |
| D2 | Target GUS for work tracker integration before Jira/Rally | Workspace already has `sf CLI` GUS skills; team uses GUS daily; Jira requires OAuth setup | 2026-03-29 |
| D3 | Make SFDX validation opt-in with graceful fallback | Avoids blocking story generation when no org session exists; preserves Phase 1 (local-only) simplicity | 2026-03-29 |
| D4 | Standardized prompts are optional accelerators, not requirements | Users must be able to type natural language; templates are shortcuts for power users | 2026-03-29 |
| D5 | Use `interview_transcript.json` (structured) instead of `.txt` (raw) | Enables programmatic consumption of Q&A pairs; searchable by downstream tools | 2026-03-29 |
| D6 | Add effort estimation to Phase 1 (SKILL.md) not Phase 2 (MCP) | Zero infrastructure needed; high value for PM/developer handoff; can be done in output template alone | 2026-03-29 |

---

*Last Updated: 2026-03-31*  
*Maintained by: Cursor AI Agent — User Story Architect*
