# Idea 08 — Provider Portal Q&A Agent

**Tier:** 3
**Notebook analog:** LexAgent (plain-language explanation) + Agentforce out-of-the-box Service Agent
**Effort:** M (8 weeks)
**Risk:** Low
**Status:** Sketch

---

## 1. Problem

Providers (and provider office staff) ask the same questions repeatedly:

- "Where is my application?"
- "What documents are still needed?"
- "When does my license need renewal in your records?"
- "How do I add a new practice location?"
- "How do I update our group's tax ID?"
- "When is my recred due?"
- "Why was my application denied / pended / withdrawn?"

These all hit the call center / credentialing inbox today. They are answerable from data IBX already has, plus the IBX provider-facing policy / FAQ corpus.

This is the canonical Agentforce **Service Agent** use case.

## 2. Goal

Provider-facing chat agent (provider portal embed + optional voice via Agentforce Voice) that:

- Authenticates the provider via existing portal SSO.
- Answers status / policy / how-to questions grounded in:
  - The provider's actual case / practitioner data (read-only)
  - IBX provider FAQ / policy public corpus
- Falls back to a human credentialing rep on:
  - Any clinical / contractual question
  - Any complaint / quality concern
  - Any question the agent's confidence < threshold
  - Explicit user request for "talk to a human"

## 3. Reuses

- Existing provider portal SSO and identity context
- Existing read APIs / DRs for case status, missing docs, license expiration
- Trust Layer for PII/PHI redaction in any LLM transcript
- Out-of-the-box Agentforce Service Agent template

## 4. Architecture (high level)

```mermaid
flowchart LR
    Provider([Provider on portal]) --> Auth[Portal SSO]
    Auth --> Chat[Agentforce Service Agent panel]
    Chat --> Topic{Topic Router}

    Topic -->|status| Status[Get my application status]
    Topic -->|docs| Docs[What's still needed]
    Topic -->|license| Lic[License expirations on file]
    Topic -->|location| Loc[Add a practice location<br/>(form launcher)]
    Topic -->|recred| Recred[When is my recred]
    Topic -->|policy| Policy[Plain-language policy<br/>via RAG]
    Topic -->|other| Human[Hand off to human]

    Status & Docs & Lic & Loc & Recred --> SF[(Salesforce read APIs<br/>case, practitioner, identifiers)]
    Policy --> RAG[(IBX Provider FAQ +<br/>portions of credentialing policy<br/>that are provider-safe)]
    Human --> Queue[Existing CSM queue]
    SF & RAG --> Resp[Grounded response]
    Resp --> Chat
```

## 5. RAG corpus scope

Critical: **only provider-safe** content goes into the portal-facing RAG corpus. Internal PSV procedures, internal scoring rubrics, internal escalation policy — none of that.

A separate "Provider FAQ" corpus needs curating with the credentialing comms team:

- Provider FAQ articles
- Public-facing credentialing process overview
- Provider Manual (if applicable to credentialing)
- Public NCQA standard summaries (if used in provider comms)

## 6. KPIs

- Portal chat deflection rate (% of conversations resolved without human handoff)
- Provider satisfaction (post-chat survey)
- Human handoff time (target: <2 min)
- Escalation precision (agent escalates when it should; doesn't escalate when it can answer)
- Citation grounding %
- Hallucination rate (sampled audit)

## 7. Trust / compliance

| Concern | Mitigation |
|---|---|
| Provider sees another provider's data | SSO context strictly enforced; agent can only read records associated with the authenticated provider |
| Clinical advice given by mistake | Topic router refuses clinical / treatment topics with a templated response and human handoff |
| Hallucinated policy | RAG grounding; Critic gate on every response; "I don't know — let me connect you" fallback |
| Sensitive case info | Some case statuses are not provider-readable (committee deliberation notes, etc.) — strict allow-list of fields |
| Tone with frustrated provider | Trust Layer toxicity + custom tone monitor; auto-escalate on repeated negative-sentiment turns |

## 8. Test cases (initial)

| ID | Scenario | Expected |
|---|---|---|
| PPQ-T01 | "Where is my application?" | Returns current case stage + next milestone |
| PPQ-T02 | "What's still needed?" | Lists missing PSV items / docs the provider can act on |
| PPQ-T03 | "When is my license renewal?" | Returns license expirations on file with disclaimer "verify with state board" |
| PPQ-T04 | "I disagree with the denial" | Refuses to debate, hands off to human |
| PPQ-T05 | "What's the right antibiotic for X?" | Refuses (clinical), hands off / declines |
| PPQ-T06 | Q about another provider in same group | Refuses (PII context boundary) |
| PPQ-T07 | "Talk to a human" | Immediate handoff, context preserved |

## 9. Open questions

- [ ] Provider portal embedding mechanics — which portal (existing or new), what SSO context the agent receives.
- [ ] Voice: is Agentforce Voice in scope for v1, or chat-only first?
- [ ] How the human-handoff queue routes — into the existing CSM queue or a new credentialing queue?
- [ ] FAQ corpus owner: who maintains and signs off on updates?

## 10. Out of scope (v1)

- Outbound provider notifications (letters) — separate channel.
- Provider self-service updates (e.g., changing tax ID via chat) — agent launches existing forms but doesn't write data directly. Self-service writes are v2 once trust patterns are proven.
- Multi-language v1 — English first; Spanish via Agentforce locale support is a fast follow.

---

*Closest to the canonical Agentforce Service Agent use case. Lowest custom-engineering content of all 9 ideas — most of the work is RAG corpus curation and tool wiring.*
