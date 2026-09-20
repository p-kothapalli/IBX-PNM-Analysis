# Notebook → Salesforce Agentforce Mapping

> Translation guide for taking a LangGraph / LangChain notebook from `~/Documents/AgenticAI/` into a production Agentforce / Agent Script implementation in IBXQA.

---

## 1. Component-by-component mapping

| Notebook primitive | Salesforce Agentforce equivalent | Notes |
|---|---|---|
| `LangGraph StateGraph` | **Agent Script** | Hybrid deterministic flow + LLM reasoning. Required-business-logic blocks always run; LLM reasoning handles nuance. |
| `add_node`, `add_edge`, `set_entry_point` | Agent Script flow control + **Topic** | Topic is the entry-point grouping; Agent Script defines the steps. |
| Supervisor node | Agentforce **Topic** with routing instructions | Topic owns the orchestration prompt. |
| Specialist agents (Credit, Income, Asset, Collateral) | Agentforce **Sub-agents** or grouped **Agent Actions** | Sub-agents have their own scoped prompts and tool sets. |
| `@tool` Python functions | **Apex Invocable Actions**, **Flows**, **DataRaptors**, **Integration Procedures** | Tools must be deterministic. Apex InvocableMethod is the most common; Flow Actions are best for declarative steps; DR for data shaping; IP for chaining DRs. |
| External-API tools (Tavily, OIG, NPI Registry) | **MCP servers** (custom or AgentExchange) | MCP standardizes external integrations. AgentExchange has pre-built ones for many systems. |
| `ChromaDB` + `RecursiveCharacterTextSplitter` | **Salesforce Knowledge** + **Data Cloud Vector DB**, or **Intelligent Context** | Intelligent Context (TDX 2026) is the new low-code unstructured ingestion pipeline — preferred if licensed. |
| `OpenAIEmbeddings` | Trust Layer–approved embedding model on Salesforce | No external embedding calls — all embeddings happen on-platform for PHI safety. |
| `MemorySaver` checkpointer | Agent Script **session state** + custom audit object | Session state for live conversation; custom object for permanent audit trail. |
| `sanitize_pii()` | **Einstein Trust Layer** masking (`Sensitive Data Detection`) | On by default for PHI/PII. Custom rules for credentialing-specific identifiers (NPI, DEA, license #) may need to be added. |
| `detect_bias_signals()` | **Trust Layer guardrails** + custom **protected-class scanner** | Trust Layer covers general toxicity/bias; we add a credentialing-specific scanner for terms like specialty, country of education, language. |
| `temperature=0` | Agent Script **Deterministic Block** + low-temp model setting | Deterministic blocks are the strongest guarantee; model temperature is a backstop. |
| `ipywidgets` HITL | **LWC** with embedded **Agentforce panel**, or **Approval Process** | LWC for analyst-in-the-loop in-flow review; Approval Process for asynchronous committee review. |
| `mortgage_test_cases.json` | **AiEvaluationDefinition** (`sf agent test create/run`) | Test specs versioned in source control alongside the agent. |
| `prints` / notebook output | **Agent Script logs** + **PRM_AgentDecision__c / PRM_AgentDecisionStep__c** custom objects | Custom audit object holds the full reasoning chain — see Audit section below. |
| `ConversationBufferMemory` | Agentforce **session memory** | Bounded by session timeout; persistent context goes to the audit object. |
| Groundedness check (LinkedIn notebook) | Final Agent Script step that re-prompts: "is every claim in the draft supported by the retrieved chunks?" | Mandatory for any agent that writes provider-facing or decision-document content. |
| Multi-agent state (`Annotated[list, operator.add]`) | Agent Script structured **session state object** with append-only fields | Same semantics, different syntax. |

---

## 2. The `PRM_AgentDecision__c` audit object

Every agent action persists a record. This is the production-grade replacement for the notebook's `reasoning_chain`. Compliance, NCQA audit, and bias monitoring all read from this.

### 2.1 `PRM_AgentDecision__c` (header)

| Field | Type | Notes |
|-------|------|-------|
| `Name` | Auto-number | `AGD-{0000000}` |
| `PRM_AgentName__c` | Text(80) | e.g. `PSV_Review_Copilot`, `Initial_Cred_Triage` |
| `PRM_AgentVersion__c` | Text(40) | Semver of the agent definition (e.g. `1.4.0`) |
| `PRM_ModelVersion__c` | Text(80) | Pinned LLM model id |
| `PRM_TriggerType__c` | Picklist | `User`, `Schedule`, `CaseEvent`, `PortalChat` |
| `PRM_RelatedCase__c` | Lookup(Case) | The credentialing case if applicable |
| `PRM_RelatedAccount__c` | Lookup(Account) | Practitioner / Vendor account if applicable |
| `PRM_StartedAt__c` | DateTime | |
| `PRM_CompletedAt__c` | DateTime | |
| `PRM_FinalDecision__c` | Picklist | `Auto`, `Assist`, `Escalate`, `Reject`, `N/A` |
| `PRM_RiskScore__c` | Number(3,0) | 0–100 |
| `PRM_HumanReviewRequired__c` | Checkbox | |
| `PRM_HumanReviewer__c` | Lookup(User) | Who reviewed |
| `PRM_HumanOverride__c` | Checkbox | TRUE if human disagreed with the agent |
| `PRM_OverrideReason__c` | Long Text | If overridden |
| `PRM_BiasFlags__c` | Long Text | JSON array of flags |
| `PRM_PolicyViolations__c` | Long Text | JSON array |
| `PRM_DecisionMemo__c` | Rich Text | Final agent-generated memo |
| `PRM_TokenUsageInput__c` | Number | For cost tracking |
| `PRM_TokenUsageOutput__c` | Number | |
| `PRM_LatencyMs__c` | Number | End-to-end |
| `PRM_AgentSchemaJson__c` | Long Text | Snapshot of agent definition at run time |

### 2.2 `PRM_AgentDecisionStep__c` (line)

Lookup to `PRM_AgentDecision__c`. One row per supervisor/specialist/critic/decision/tool step.

| Field | Type | Notes |
|-------|------|-------|
| `PRM_Decision__c` | Master-detail | Header |
| `PRM_StepIndex__c` | Number | Order |
| `PRM_StepName__c` | Text | e.g. `LicenseVerifier`, `Critic`, `Tool:NPPESLookup` |
| `PRM_StepType__c` | Picklist | `Supervisor`, `Specialist`, `Critic`, `Decision`, `Tool`, `RAG`, `HITL` |
| `PRM_PromptHash__c` | Text(64) | SHA-256 of the prompt template version |
| `PRM_InputJson__c` | Long Text | |
| `PRM_OutputJson__c` | Long Text | |
| `PRM_RagCitations__c` | Long Text | JSON array of `{sourceId, chunkId, sourceTitle, score}` |
| `PRM_ToolCallsJson__c` | Long Text | If specialist invoked tools, the call list |
| `PRM_BiasFlagsThisStep__c` | Long Text | |
| `PRM_LatencyMs__c` | Number | |
| `PRM_TokenUsage__c` | Number | |
| `PRM_StartedAt__c` | DateTime | |
| `PRM_CompletedAt__c` | DateTime | |

### 2.3 Why a custom object instead of out-of-the-box agent logs

- NCQA / state regulator audit requires us to keep a full reasoning chain for **years**, queryable by case, by provider, by date, by agent version. Out-of-the-box agent logs are operational telemetry, not retention-grade audit.
- Bias / fairness monitoring runs SOQL aggregations across this object weekly.
- Override rate tracking (do analysts disagree with the agent?) drives prompt iteration.

---

## 3. Tool wrapping recipes

Patterns for converting a notebook `@tool` into a production Agentforce action.

### 3.1 Pure calculation tool (`calculate_dti_ratio`-style)

**Notebook:**
```python
@tool
def calculate_dti_ratio(monthly_income: float, total_debts: float, proposed_payment: float) -> dict:
    ...
```

**Production:** Apex InvocableMethod.

```apex
public class PRM_CalculateRatiosAction {
    public class Request {
        @InvocableVariable(required=true) public Decimal monthlyIncome;
        @InvocableVariable(required=true) public Decimal totalDebts;
        @InvocableVariable(required=true) public Decimal proposedPayment;
    }
    public class Response {
        @InvocableVariable public Decimal ratio;
        @InvocableVariable public String tier;
        @InvocableVariable public String explanation;
    }
    @InvocableMethod(label='PRM Calculate DTI Ratio'
                    description='Returns DTI ratio + tier classification'
                    callout=false)
    public static List<Response> calculate(List<Request> reqs) { ... }
}
```

Same pattern for any pure calculation: license-expiry check, malpractice-claim threshold check, gap-in-employment-history calculation.

### 3.2 External-API tool (`get_stock_price`-style)

**Notebook:**
```python
@tool
def get_stock_price(ticker: str) -> dict:
    return yfinance.Ticker(ticker).info
```

**Production:** MCP server (preferred) OR Apex callout to Integration Procedure.

```apex
@InvocableMethod(label='NPPES NPI Lookup' callout=true)
public static List<NPPESResponse> lookup(List<NPPESRequest> reqs) {
    // Delegates to existing PRM_NPPESLookupController or new MCP-backed callout
}
```

If the external system is high-traffic, prefer **MCP** so multiple agents share the same connector and rate-limiting/caching layer.

### 3.3 RAG tool (`query_private_database`-style)

**Notebook:**
```python
@tool
def query_private_database(question: str) -> dict:
    docs = retriever.invoke(question)
    return llm_with_citations(question, docs)
```

**Production:** Out-of-the-box if Intelligent Context is licensed. Otherwise:

- Stand up a Data Cloud Vector index per RAG corpus (e.g., `IDX_NCQA_Standards`, `IDX_IBX_CredPolicy`, `IDX_StateRules_NJ`).
- Wrap retrieval in an Apex action that returns `{chunks: [{text, sourceId, score}], grounding_required: true}`.
- The Critic step verifies every claim cites a returned `sourceId` — reject the response if not.

### 3.4 Multi-source RAG with jurisdiction filter (LexAgent-style)

```apex
@InvocableMethod(label='PRM Policy RAG Query')
public static List<RAGResponse> query(List<RAGRequest> reqs) {
    // Each request: question, list of corpora to search, optional jurisdiction filter
    // Each response: ranked chunks with corpus, jurisdiction, sourceId, score
}
```

The agent's prompt instructs it to call this with the appropriate jurisdiction (e.g., NJ for a NJ-based provider). Critic verifies retrieved jurisdiction matches the case's jurisdiction.

---

## 4. Agent Script skeleton (for any new agent in this folder)

```yaml
# Pseudocode — actual syntax follows Agent Script grammar
agent: PSV_Review_Copilot
version: 1.0.0
description: Drafts PSV review notes for credentialing analyst
model: <pinned-trust-layer-approved-model>
temperature: 0

trust_layer:
  pii_redaction: required
  toxicity_check: required
  custom_scanners:
    - PRM_BiasScanner        # protected-class terms in credentialing context
    - PRM_PolicyCitationScanner  # rejects responses that cite policies not in retrieved chunks

deterministic_pre:
  - load_case_context           # Apex: pull Case, Practitioner, current PSV state
  - audit_start                 # insert PRM_AgentDecision__c header

topic: Researcher
  instructions: |
    Pull every PSV source for this practitioner. ...
  actions:
    - PRM_NPPESLookup
    - PRM_OIGLeieCheck
    - PRM_StateBoardLicenseCheck
    - PRM_DEACheck
    - PRM_ABMSCheck
    - PRM_NPDBCheck
  on_complete: -> Writer

topic: Writer
  instructions: |
    Draft PSV review notes ...
  rag_corpora:
    - IDX_NCQA_Standards
    - IDX_IBX_CredPolicy
  on_complete: -> Critic

topic: Critic
  instructions: |
    For every claim in the draft, verify the cited source exists in the retrieved chunks.
    Reject any uncited claim. Score risk 0-100. Run bias scanner.
  on_complete: -> Decision

topic: Decision
  instructions: |
    Synthesize. Set human_review_required=true if risk_score > 30 or any policy_violations.
  output_schema: PRM_AgentDecisionOutput

deterministic_post:
  - audit_complete              # close PRM_AgentDecision__c, fan out steps
  - notify_analyst              # Platform Event for LWC subscription
```

---

## 5. Testing pattern

| Notebook | Production |
|---|---|
| `mortgage_test_cases.json` with 3 cases (APPROVED / CONDITIONAL / REJECTED) | `AiEvaluationDefinition` metadata with N labeled scenarios per agent |
| Run notebook end-to-end in Colab | `sf agent test run --evaluation-name PSV_Review_Copilot_Eval` |
| Manual inspection of state | **Eval metrics**: accuracy vs. labeled outcome, citation-grounding rate, bias-flag rate, latency, token cost |
| One-off notebook run | **Batch eval** in CI (per PR), gated on regression metrics |

Add a regression eval to CI: every PR that touches an agent definition must pass the eval suite. Failure blocks merge.

---

## 6. Deployment / lifecycle

| Phase | Notebook | Production |
|---|---|---|
| Author | `.ipynb` | `.agent` file + Agent Script + tied Apex/Flows/DRs |
| Version | Git on the notebook | Git on the bundle; **agent version pinned in `PRM_AgentDecision__c.PRM_AgentVersion__c`** |
| Test | Run cells | `sf agent test run` in CI |
| Deploy | Re-run notebook | `sf agent publish` to QA → UAT → Prod |
| Observe | `print()` | `sf agent test results` + Data Cloud session traces + `PRM_AgentDecision__c` queries |
| Iterate | Edit cells, re-run | Edit prompt/flow → eval → publish; rollback by republishing prior version tag |

---

## 7. Skills available in the workspace that accelerate this work

The workspace already has these skills — read them at the start of any agent build:

- `developing-agentforce` — how to author `.agent` files, Agent Spec, sub-agents/topics/actions, Agent Script CLI commands.
- `testing-agentforce` — how to write `AiEvaluationDefinition` test specs and interpret results.
- `observing-agentforce` — how to query Data Cloud session traces and analyze production behavior.

These three skills cover the full author → test → observe loop and should be the first read for any engineer picking up an idea from this folder.

---

*See `ideas/Idea01_PSV_Review_Copilot.md` for the first concrete application of this mapping.*
