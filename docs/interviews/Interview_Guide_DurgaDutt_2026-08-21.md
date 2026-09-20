# Interview Guide — Durga Dutt (Salesforce Industries Technical Architect)

**Date:** Aug 21, 2026 · **Duration:** 60 minutes · **Format:** scenario-based

**Candidate:** 14+ yrs IT, 7+ yrs OmniStudio/Vlocity (Huron — insurance). Led teams of 10. Built a JS mixin framework for OmniScript reactivity, an Agentforce + Azure DevOps automated code-review pipeline, and a RAG solution-architecture tool.

**Two orgs in play:**
- **CLSTG (`clstage`) — Companion Life Insurance Company.** Group benefits quoting: census upload, multi-product rating, proposal PDF generation. This is his exact domain (census management, DocGen, insurance quoting). All numbers below are **live from the org, verified today**.
- **IBX PRM** — provider network management; re-platforming OmniStudio record-creation onto layered Apex + a metadata-driven async engine.

**What we're testing:**
1. Has he personally hit — and fixed — OmniStudio collapsing at volume, or only architected happy paths?
2. Does he think in idempotency, partial failure, and recovery, or only "make it work"?
3. Is his AI experience engineered (guardrails, evals, verification) or demo-ware?

> **Confidentiality note:** the CLSTG scenarios below are framed as "an org we run." That's fine to describe functionally. Don't share record IDs or client-identifying detail before he's under NDA — the numbers alone carry the scenario.

---

## Ground truth from CLSTG (verified live, Aug 21 2026)

Keep this table in front of you. When he generalises, pull him back to these numbers.

| Fact | Value |
|---|---|
| Group censuses | **7,872** |
| Census member rows (`vlocity_ins__GroupCensusMember__c`) | **565,223** |
| Largest single census | **12,668 members** |
| Second largest | **12,668 members** — a *different* census, uploaded the next day |
| Fields on the census member object | **109**, incl. ~12 product-option picklists + per-plan rate fields (`CL_2001_Initial_1KRate__c`, `CL_5000_Updated_1KRate__c`, …) |
| Quotes / Quote Line Items | 8,207 / **130,155** |
| Rate-calc staging (`CL_CalculateRatesBatchStaging__c`) | 1,287 Completed · **608 Error (32%)** · **12 stuck "In Progress"** |
| Staging design | `QuoteId__c`, `ResultJSON__c` (**Long Text, 131,072 cap**), `Status__c`, `LastPingedByUI__c`, `CL_HasQuotingFlowFinished__c`, `CL_InstanceIdentifier__c` |
| Document generation | 7,127 Success / **46 Failure** (0.64%) |
| Rating pushed to async | IPs literally named `CLQueuable/GetRatedProducts` v13, `CLQueuable/RepricingProducts` v14, `CLQueuable/RepricingProductsWithUserInputs` v9 |
| Batch rating | `CL_Batch/InitializeCalcPrice` v8 → `CL_Batch/HandleRatesMerge` v8 → Apex `CL_BatchCalcPrice` (**77,744 chars**) |
| The tell | An OmniScript named **"Get Proposal if delayed due to Batch"** (`CLBroker/GetProposal` v21) |
| Census re-upload | OmniScript `cl/CensusReupload` v1 → IP `CL_HandleQLI/PostCensusReupload` v8 |
| Largest service class | `CensusMemberService` — **178,564 chars**; its test class **293,949 chars** |
| Version churn | `CL_IP_Get/QuoteInfoAndClone` **v31**, `CL_Dental/GetQuoteDetails` **v27**, `CL_IP_Update/Quote` **v25** |

---

## Timebox

| Time | Segment | Min |
|---|---|---|
| 0:00–0:04 | Calibration | 4 |
| 0:04–0:20 | Census & volume scenarios (CLSTG-grounded) | 16 |
| 0:20–0:34 | Contention, idempotency, async recovery (PRM) | 14 |
| 0:34–0:51 | AI-assisted development + code-review exercise | 17 |
| 0:51–0:57 | Leadership & cutover | 6 |
| 0:57–1:00 | His questions | 3 |

> **Must-ask six if you fall behind:** S2, S3, S5, S7, A2, and the code-review exercise (A6).

---

# Segment 1 — Calibration (4 min)

### S1. Opening scenario

> "Forget titles for a moment. Picture the largest single submission that ever went through a system you built — the biggest census, the biggest roster, the biggest batch. How many rows was it, and what broke first?"

**Model answer:** A specific number and a specific first failure — "a 9,000-life census; the rating IP hit CPU timeout at about 1,200 members, so we moved rating into a Queueable chain and staged results." Names the limit, the symptom, the fix.

**Strong signals:** Numbers without prompting. Distinguishes what broke *first* from what broke *next* — that ordering shows he actually profiled it.

**🚩 Red flags:** Only patterns and principles, no numbers. "We followed best practices and didn't have issues" at 500K+ record scale is either a much smaller system than claimed or he wasn't close to the failures.

---

# Segment 2 — Census & volume (16 min, CLSTG-grounded)

This is his home turf. If he's strong anywhere, it's here — so raise the bar accordingly.

### S2. The 12,668-life census *(must-ask, 5 min)*

> **Scenario:** "You've joined us Monday. We run group benefits quoting on Vlocity Insurance. A broker uploads a census — 12,668 members, one file. Each member row carries about a dozen product elections: Dental, Vision, Life, STD, LTD, Accident, Critical Illness, Vol Life, Vol AD&D. For each elected product we have to run a rating procedure and write rate fields back onto the member, then roll those up into quote line items.
>
> Right now the flow is OmniScript → Integration Procedure → DataRaptor Loads. The broker clicks Rate and waits. Tell me what happens."

**Model answer — the failure cascade, in order:**
1. **CPU timeout (10s sync) hits first.** DataRaptor transform chaining is CPU-hungry; 12,668 rows × 12 products of formula/mapping work blows the CPU budget long before any row limit. This is almost always the first wall in a DR-heavy flow.
2. **SOQL 50,000-row retrieval limit** — pulling 12,668 members plus their group classes, products, and rate tables into one context.
3. **Heap (6MB sync / 12MB async)** — the member JSON alone at 109 fields × 12,668 rows will not fit; the IP passes the whole payload between steps by value.
4. **DML rows (10,000)** — 12,668 member updates *cannot* be done in one transaction at all. Not a tuning problem; a hard ceiling.
5. **DML statements (150)** if any DR is invoked per-record inside a loop — that's the classic OmniStudio anti-pattern and it fails at 150 members, not 12,668.
6. **Viewstate / request timeout (120s)** on the browser side even if you somehow survived the rest.

**The conclusion we want:** *You cannot fit this in one transaction at any batch size.* The only correct shape is chunked async on a fresh governor budget per chunk, with the UI decoupled from completion. Then, either unprompted or on prompting, the design:
- Chunk by member (Batch Apex, scope ~200, or 500 if the per-row work is light).
- Rate per **product × group class**, not per member — most members in a class share a rate, so you compute a small rate matrix once and apply it, turning an O(members × products) problem into O(classes × products) plus a cheap join. **This is the single best answer available and few will give it.**
- Persist progress to a staging record so the UI can poll.
- One bulk DML per object type per chunk.

**Strong signals:** Asks clarifying questions before designing — "does the broker need to wait for the result, or can we notify them?", "how many distinct group classes?", "are rates deterministic per class or per member age?" Recognises the O(members) → O(classes) collapse. Names CPU as the *first* failure, not DML.

**🚩 Red flags:** "Increase the batch size." "Use `@future`." Reaches for Batch Apex without first questioning whether per-member rating is necessary at all. Cannot rank the limits.

**Follow-up:** *"Now the broker says they need the rates on screen in under 30 seconds."* → Want: pre-computed rate matrix, optimistic display of class-level rates while member-level detail finishes async, or an honest renegotiation of the requirement. Watch whether he pushes back on the business ask instead of silently promising the impossible.

---

### S3. The 32% failure rate *(must-ask, 5 min)*

> **Scenario:** "Here's the real state of that org today. Rating was already moved off the synchronous path into a batch with a staging object — one row per quote, holding a status, a result JSON, and a timestamp the UI pings while it polls.
>
> The numbers: **1,287 Completed, 608 Error, 12 stuck In Progress.** That's a 32% error rate, and those 12 have been In Progress long enough that nobody believes they're still running.
>
> It's your first week and this is your problem. What do you do, in what order?"

**Model answer:**

*Triage before redesign — the ordering matters more than the answer:*
1. **Classify the 608 errors before touching code.** Group by error text, by quote size, by product mix, by date. A 32% failure rate is almost never 608 unique bugs — it'll be two or three causes. If the staging row doesn't capture enough to classify (just "Error" with no message), **that's finding number one** and the first fix.
2. **The 12 stuck In Progress are the more serious defect.** A job that fails is visible; a job that hangs is invisible and un-actionable. Causes: the batch died in a way that never wrote a terminal status (uncatchable governor `LimitException`, which you *cannot* catch and recover from inside the failing transaction), or the process was killed, or `finish()` threw. Fix: write status transitions **defensively** — set the terminal status from `finish()`, which still runs after failed chunks, and add a **watchdog** (scheduled job) that ages out anything In Progress past an SLA and marks it Failed so it becomes visible and retryable.
3. **Suspect the `ResultJSON__c` Long Text cap of 131,072 characters.** For a 12,668-member census the result payload will exceed 128KB and the write throws `STRING_TOO_LONG`. This is a *size-correlated* failure — test the hypothesis by correlating errors against census size. If it holds, move the payload to a **ContentVersion file** (or chunk it), and keep only status and a summary on the record.
4. **Check idempotency before enabling any retry.** If re-running a quote's rating re-creates rather than updates, mass-retrying 608 rows doubles the damage.
5. **Then instrument:** error message + stack + chunk index captured on the staging row, a dashboard on status, and an alert on error rate — so you never again discover a 32% failure rate by running a query.

**Strong signals:**
- Goes to **classify-then-fix**, not straight to a redesign.
- Treats the 12 stuck rows as **worse** than the 608 errors, and can explain why an uncatchable `LimitException` leaves no terminal status.
- **Spots the 131,072 Long Text cap unprompted.** This is a top-decile signal — it's the same failure we designed around on the IBX side by moving payloads to ContentVersion.
- Mentions a watchdog/reaper for stuck jobs.
- Asks "what's the business impact — are brokers seeing stale rates, or no rates?" before prioritising.

**🚩 Red flags:** "Add a try-catch and retry" as the whole answer. Rewrites the framework before understanding the failures. Doesn't notice that a 32% error rate means the feature is effectively broken and someone has been living with it.

**Follow-up:** *"You believe you can catch a governor limit exception and log it. Can you?"* → Correct answer: **no** — `System.LimitException` is uncatchable and rolls back the transaction; that's precisely why status must be written from `finish()` or a watchdog, not from a catch block. This is a sharp, fast competence check.

---

### S4. "Get Proposal if delayed due to Batch" (3 min)

> **Scenario:** "In that same org there's an OmniScript in production whose actual name is *'Get Proposal if delayed due to Batch'*. It's on version 21. What does the existence of that component tell you, and what would you do about it?"

**Model answer:** It's a **workaround that became permanent**. Someone made rating async to survive volume, but the UX contract was never redesigned around asynchrony — so the "your thing isn't ready yet" path got bolted on as a separate user-facing flow rather than being the *normal* flow. Version 21 says it's been patched twenty times, which means it's load-bearing and fragile.

The fix is to invert the model: **asynchronous is the only path**. Submit returns immediately with a tracked job; the UI shows progress and completion (poll, or better, push via Platform Event / `empApi` / Custom Notification); the "delayed" branch disappears because there is no non-delayed branch. One flow, one state machine.

**Strong signals:** Reads organisational history out of a component name — that's an architect's instinct. Notes that polling via a `LastPingedByUI__c` timestamp is a smell (chatty, races, no push) and proposes Platform Events or `empApi` subscription instead. Recognises the parallel to what we're doing on the IBX side: async-only, no dual path.

**🚩 Red flags:** Treats it as a naming problem. Doesn't see that two code paths for the same outcome doubles the test surface and guarantees drift.

---

### S5. The duplicate 12,668 census *(must-ask, 3 min)*

> **Scenario:** "Two censuses in the org have exactly 12,668 members each. Same size, uploaded a day apart. There's a 'Census Reupload' OmniScript and a 'Post Census Reupload' Integration Procedure in the flow.
>
> Broker uploads a corrected census for the same quote. What should happen, what probably *is* happening, and how do you make the right thing structurally guaranteed?"

**Model answer:**
- **What's probably happening:** the re-upload creates a *second* census with 12,668 new member rows rather than reconciling against the first. The org now carries 25,336 rows for one employer group, quote line items may point at the stale census, and any rate comparison silently uses whichever the query happens to find. That's a correctness bug, not just bloat.
- **What should happen:** the upload is keyed on a stable business identity — quote + employer + census version — and reconciled as a **three-way diff**: members added, members changed, members removed. Removals matter most; a naive upsert leaves terminated employees rated and priced forever.
- **Structural guarantee:** an **External Id** on the member (e.g. quote + SSN/employee id hash) so the load is an idempotent upsert, plus an explicit versioning model — either supersede the prior census with a status and repoint the quote atomically, or upsert in place with an audit trail. Never "create new and hope the right one is queried."
- Then the question that separates good from great: **"what happens to rates and quote line items already derived from the old census?"** They must be invalidated and recomputed, or you have a quote whose numbers don't match its census.

**Strong signals:** Immediately reaches for a deterministic key and upsert semantics rather than detect-then-branch. Raises the **delete/termination** case unprompted (most people only handle add and update). Asks about downstream derived data (QLIs, rates, generated proposals).

**🚩 Red flags:** "Add a duplicate rule." Proposes detecting existence with a SOQL query and branching — this is exactly the bug class in S7; if he proposes it here, use S7 to show him why it fails and see if he self-corrects.

---

# Segment 3 — Contention, idempotency, recovery (14 min, PRM-grounded)

Shift context: *"Different org, different domain — provider network management. Same class of problem."*

### S6. Lock contention (4 min)

> **Scenario:** "A practitioner submission runs through two sub-Integration-Procedures. Both of them write to the same shared Case Data Manager record during the same submission. Single user, it's fine. Under concurrent submissions we get `UNABLE_TO_LOCK_ROW`, intermittently, and never in UAT. Diagnose and fix."

**Model answer, in the order a good architect works:**
1. **Diagnose before fixing.** Is it a direct row lock on the shared record, or **parent lock escalation** — inserting/updating many children of a master-detail (or a lookup with sharing-relevant rollups) implicitly locks the parent? The second is the subtler and more common cause, and the fix is different.
2. **Coalesce the writes.** The real defect is that two independent DR steps each write the shared record. Hold the state in memory through the unit of work and issue **one** DML at the end. This is the actual fix; everything else is mitigation.
3. **Serialize deliberately** where genuine concurrency exists — `FOR UPDATE` to queue rather than collide, or route all writes to that record through a single-threaded async lane (a Queueable chain, or a batch scoped by the shared record) so only one writer exists at a time.
4. **Order DML consistently** by parent id across chunks so concurrent transactions don't interleave and deadlock.
5. **Only then** retry with backoff — and say out loud that retry is a band-aid over a design flaw.
6. **Why UAT missed it:** single-threaded testing. Concurrency bugs need concurrent tests — fire parallel submissions deliberately.

**Strong signals:** Distinguishes row lock from parent-lock escalation. Says "one DML at the end of the unit of work" before saying "retry." Notes that the test gap is as important as the code fix.

**🚩 Red flags:** Jumps to catch-and-retry. Suggests `without sharing` (irrelevant — it's locking, not visibility). Doesn't ask whether the two writers can be merged.

---

### S7. The duplicate-record trap *(must-ask, 5 min)*

This is a real production failure — 19 blocked submissions. Give him the evidence and let him work.

> **Scenario:** "Nineteen form submissions fail in production. Three distinct errors:
>
> **(a)** `duplicate value found: HealthCloudGA__SourceSystemId__c duplicates value on record with id: 001UW...` — the form has 'existing NPI' detection: a DataRaptor that joins a provider-NPI record to its Account. It returned nothing, so the flow took the create-new-Account path. But the Account plainly exists, keyed on that same NPI in a unique External Id.
>
> **(b)** `duplicate value found: SourceSystemIdentifier` on a provider record, where a before-insert trigger computes that identifier from Tax Id plus Account Name.
>
> **(c)** `Duplicated results found for HealthcareProviderTaxonomy AccountId=… AND TaxonomyId=… — Related Ids: 0bP…, 0bP…`
>
> Root-cause each, then tell me how you make this whole class of bug impossible."

**Model answer:**

- **(a) The detection key and the uniqueness key are different.** Existence is *detected* via a linkage record (provider-NPI → Account) that can be missing or broken; existence is *enforced* by the database on a different field (the External Id). Whenever your "does this exist?" predicate diverges from the constraint the database actually enforces, you will eventually take the wrong branch — and the DB will veto you.
- **(b) Same disease, different organ.** The uniqueness value is computed by a trigger from Tax Id + Account Name, so the caller cannot know in advance whether it will collide. Uniqueness derived downstream of the decision point is undetectable at the decision point.
- **(c) An upsert whose match key isn't actually unique.** Two rows already exist for the same (Account, Taxonomy) pair; the DataRaptor Load engine matches 2+, can't choose, and throws. Note this is **pre-existing dirty data**, so it needs cleanup *and* prevention.

**The structural fix — this is the answer we want:**
> **Stop branching on a query. Upsert on the External Id and let the database's unique key be the single source of truth for existence.** The detection logic then becomes cosmetic — it drives UI messaging, not correctness. If the branch is wrong, the upsert still does the right thing.

Plus: for (b), move the derived identifier computation *upstream* so the caller can key on it, or make it the External Id itself. For (c), clean the duplicates and add a real uniqueness guarantee — a unique composite External Id — rather than adding more match fields to the DataRaptor.

**The connection that marks a top candidate:** *"…and this also means any retry in your async chain is unsafe until these are upserts — a resumed batch would re-create everything the first attempt already wrote."* If he links idempotency to retry safety unprompted, that's the strongest signal in the whole interview.

**Strong signals:** Articulates the detect-vs-enforce mismatch as a general principle, not three separate bugfixes. Distinguishes the dirty-data problem (c) from the design problems (a) and (b). Connects to retry safety.

**🚩 Red flags:** Fixes each error separately. Proposes "query harder" — add fallback lookups on more fields — which just moves the race. Doesn't notice (c) is a data problem.

---

### S8. Designing the recovery model (5 min)

> **Scenario:** "We're rebuilding this as async-only: five sequential batch steps. The chain **halts on the first failure** — later steps don't run, completed steps keep their records, there's no compensating rollback, and retry is manual and resumes from the failed step.
>
> A stakeholder says that's unacceptable — they want all-or-nothing. Argue the case, either way."

**Model answer:** The trade is deliberate and defensible: **whole-submission atomicity is impossible across async boundaries** (savepoints don't span transactions), so the real choice is between synchronous atomicity that *cannot handle the volume* and asynchronous durability that can. You buy scale and resumable recovery; you pay with intermediate states.

What makes that safe is not rollback, it's:
- **Idempotency** — resume must not double-create (External-Id upserts + status guards so a Completed step is never reprocessed).
- **Visibility of incompleteness** — a status on the parent record so no downstream consumer treats a half-built provider as real. This is what actually addresses the stakeholder's fear; they don't want atomicity, they want *"nothing broken becomes visible."*
- **Observability and a retry path** — job/step records, an error surface, and a human-operable retry.

Compensating transactions are usually **worse** than forward recovery in Salesforce: the compensation itself can fail, needs its own idempotency, and doubles the code you must test.

**Strong signals:** Knows savepoints can't span transactions. Reframes the stakeholder's demand into the requirement behind it (visibility, not atomicity). Argues *against* compensating transactions with reasons. Asks what the business actually does with a half-created record.

**🚩 Red flags:** Insists on cross-transaction savepoints (not possible). Accepts the design without probing. Or rejects it without proposing anything that survives 12,668 rows.

**Quick follow-up (30 sec):** *"The job insert fires a trigger that starts the batch. What breaks?"* → The payload and child records may not be committed yet, and you can't call `Database.executeBatch` cleanly from a trigger context. Start async **after** the unit of work commits, from a one-shot Queueable.

---

# Segment 4 — AI-assisted development (17 min)

~9 minutes of questions, ~8 minutes hands-on. He claims an Agentforce code-review pipeline and a RAG tool — push past the headline on both.

### A1. His actual loop (3 min)

> **Scenario:** "Take the last non-trivial thing you shipped with AI in the loop. Narrate it like a screen recording — what you typed, what it gave you, what you kept, what you threw away."

**Model answer:** A real, staged loop: ground the model in project context first (rules/instructions file, retrieved org metadata, existing conventions) → get a **plan** and review the plan before any code → implement in small increments → a verification gate after each (compile/deploy-validate, tests, static analysis) → human review of the diff. Plus a clear statement of what he does *not* delegate.

**Strong signals:** Separates planning from implementation. Mentions grounding/context as a deliberate step, not an afterthought. Can name something the AI got wrong and how he caught it. Talks about diff size — small diffs because large ones defeat review.

**🚩 Red flags:** "I paste the requirement and it writes the class." No verification step. Can't recall a failure.

---

### A2. Hallucinated metadata *(must-ask, 3 min)*

> **Scenario:** "Our number-one AI failure mode on Salesforce work: the model invents API names with total confidence. It writes a field that doesn't exist, or references a DataRaptor nobody created. It looks right, it reads right, and it fails at deploy — or worse, it deploys against a *similar* field and silently writes the wrong data.
>
> You're setting the standard for a team of ten. How do you engineer this out?"

**Model answer:**
- **Ground, don't trust.** Pull real metadata into context — retrieve source, schema describes, an indexed manifest of objects/fields/components — so the model *reads* names instead of recalling them. Retrieval beats prompting.
- **Constrain via project rules** — a committed instructions/rules file that forbids inventing `__c` names and requires verification against source. Everyone on the team inherits it; it's version-controlled, so the standard is reviewable.
- **Tooling over memory** — MCP tools or a code index so lookups are a tool call.
- **A deterministic gate is the real control.** The model is *allowed* to be wrong; the pipeline is not allowed to let it through. Deploy-validate (`--dry-run`), Salesforce Code Analyzer / PMD, and tests in CI. Guardrails you can't bypass beat instructions you can.
- **OmniStudio-specific trap:** many versions exist per asset and **only the active one is live**. An AI grounded on an inactive version produces confidently wrong output. Given CLSTG has components at v21, v25, v27, v31, this matters enormously — ask him directly if he doesn't raise it.

**Strong signals:** Says some version of *"prompting reduces the error rate; the gate eliminates the escape."* Raises the active-version problem. Distinguishes deploy-time failures (annoying) from silent wrong-field writes (dangerous).

**🚩 Red flags:** "Better prompts." "Tell it to be careful." Relies solely on human review to catch it.

---

### A3. His Agentforce code-review pipeline (4 min)

> **Scenario:** "You built automated code review with Agentforce in Azure DevOps. Suppose I'm the sceptical engineer on your team: I've had three of its comments be wrong this week and I've started ignoring it. Talk me down — and tell me what you actually did when this happened."

Probe hard; this is the most checkable claim on the resume:
- "Give me two specific rules it enforced, and one real defect it caught that a human missed."
- "**What was the false-positive rate?**" — anyone who has genuinely shipped an automated reviewer has a noise story. No noise story ≈ no production deployment.
- "Advisory or blocking? Who made that call, and did you change it?"
- "Same PR twice — same review? How did you handle non-determinism?"
- "What did you deliberately keep in deterministic linters instead of the LLM?"
- "Cost per PR — did anyone check?"

**Model answer:** Mature answer is that the LLM handles what linters can't — intent, missing test cases, design smells, naming, requirement mismatch — while **style, security scanning, and limit-pattern detection stay in PMD / Code Analyzer** because they must be deterministic and cheap. It starts advisory, earns trust, and only becomes blocking for the narrow high-precision rules. Noise is managed by cutting scope, not by adding prompt text. He should be able to describe tuning it *down*.

**Strong signals:** Owns the noise problem and describes a specific tuning decision. Knows which checks don't belong in an LLM. Measured something.

**🚩 Red flags:** No false-positive story. "It reviewed everything." Can't name a real defect it caught. Blocking-from-day-one with no trust-building.

---

### A4. RAG honesty (2 min)

> **Scenario:** "Your RAG architecture tool tells an engineer to use a pattern. He follows it and it's wrong for our org. How would you have known before he did?"

**Model answer:** Evaluation, not vibes: a golden set of questions with known-good answers, retrieval hit-rate measured, periodic human spot-checks, and — most importantly — **citations back to source** so the engineer can verify in one click rather than trusting the summary. Plus a freshness/re-index strategy, because stale architecture guidance is worse than none.

**Strong signals:** Has an eval story. Insists on citations. Mentions index staleness.

**🚩 Red flags:** "Users liked it." No measurement. Doesn't distinguish retrieval failure from generation failure.

---

### A5. Limits and judgment (2 min)

> **Scenario:** "Where has AI actively cost you time or quality? And on a healthcare or insurance project handling member data — what would you never let it touch?"

**Model answer:** Genuine examples — large refactors where it silently drops edge cases; tests written to pass rather than to assert; confident wrongness on OmniStudio internals; review fatigue on big diffs so defects slip through *because* velocity went up. On data: **PHI/PII must not leave approved boundaries** — be deliberate about what enters prompts and logs, use sanitised or synthetic fixtures, and require human sign-off on anything touching underwriting, credentialing, or compliance decisions.

**Strong signals:** Names the review-fatigue paradox — that faster generation can *lower* quality if review capacity doesn't scale. Treats member data as a hard boundary without being led there.

**🚩 Red flags:** "It's never hurt, it's always faster." That's a maturity tell, not a capability claim.

---

### A6. Hands-on code review *(must-ask, 8 min)*

Share this. Say: *"An AI agent produced this for our provider project. You're the reviewing architect — talk me through what goes back."*

```apex
public class PRM_PractitionerFacilityService {

    public static void createFacilities(List<Map<String, Object>> rows) {
        for (Map<String, Object> row : rows) {
            Account acct = [
                SELECT Id, Name FROM Account
                WHERE HealthCloudGA__SourceSystemId__c = :(String) row.get('npi')
            ];

            HealthcarePractitionerFacility hpf = new HealthcarePractitionerFacility();
            hpf.PractitionerId = acct.Id;
            hpf.RecordTypeId = '012UW000000XyZaYAK';
            hpf.Status = 'Active';
            insert hpf;
        }
    }
}
```

**Scoring key:**

| # | Finding | Tier |
|---|---|---|
| 1 | SOQL inside a loop — fails at 100 rows | Must catch |
| 2 | DML inside a loop — fails at 150 rows | Must catch |
| 3 | Not bulkified: should be one query into a `Map<String, Account>` keyed by NPI, build a `List<>`, one `insert` | Must catch |
| 4 | Hardcoded RecordTypeId — breaks in every other org; resolve by DeveloperName via cached describe | Must catch |
| 5 | Assignment-form SOQL throws `QueryException` on **zero** rows *and* on **2+** rows — and we know from S7 that duplicates exist in this org | Strong |
| 6 | No sharing declaration — should be `with sharing` | Strong |
| 7 | No CRUD/FLS enforcement — `WITH USER_MODE` or `stripInaccessible` | Strong |
| 8 | **Not idempotent** — a resumed batch double-creates every facility. Needs External-Id upsert | Excellent |
| 9 | All-or-nothing insert: one bad row fails 199 good ones. Consider `Database.insert(list, false)` and route failures to the error/DLQ path | Excellent |
| 10 | No error handling or logging; static method; untyped `Map<String, Object>` instead of a typed payload | Nice to have |

**Interpretation:**
- **1–4 findings** → sees syntax, not systems. Concerning at architect level.
- **5–7** → solid senior developer.
- **8+, especially #8 and #9** → architect. He's reasoning about the failure and recovery path, not just the happy path.

**Then the meta-question — don't skip it:**
> "Now write me the rule that stops the AI producing this in the first place."

**Model answer:** A specific, checkable rule set — bulkification mandate, no hardcoded IDs, sharing + FLS required, idempotent upserts on External Id, one bulk DML per object type, partial-success handling for bulk paths — **plus** the recognition that a committed rules file *and a CI static-analysis gate* beat a longer prompt, because prompts drift and gates don't. Best answer notes that findings 1, 2, 4, 6 are catchable deterministically by PMD/Code Analyzer and should never rely on an LLM at all.

---

# Segment 5 — Leadership & cutover (6 min)

### L1. The reskilling problem (3 min)

> **Scenario:** "Ten engineers, most fluent in OmniStudio, few strong in Apex. We're moving from declarative record-creation to layered Apex services. Two of your seniors think this is over-engineering and that the DataRaptors are fine. Delivery can't stop for the transition. How do you run it?"

**Model answer:** A reference implementation first — one vertical slice built to the target standard that people can copy, because abstract standards don't transfer. Then pairing, a strict definition-of-done, review standards, and **incremental conversion epic by epic**, never a big bang. On the sceptics: don't argue architecture, argue evidence — show them the 32% error rate, the 12,668-row ceiling, the untestable DR chain. And concede where they're right: DataRaptors *are* fine for bounded, simple loads, and keeping them there is the honest position.

**Strong signals:** Reference implementation before mandate. Uses data to persuade, not authority. Concedes the valid part of the objection. Honest about the reskilling cost and timeline hit.

**🚩 Red flags:** "I'd set the standard and enforce it in code review." Pure top-down. No acknowledgment that this slows delivery before it speeds it up.

---

### L2. Cutover (3 min)

> **Scenario:** "Hard cutover — we re-point the OmniScript's remote action from the legacy chain to the new Apex intake. No feature flag; rollback is re-pointing it back. You're signing off. What do you demand first, and would you challenge the no-flag decision?"

**Model answer:** Before sign-off: **shadow/dual-run parity** over a real period, with field-by-field record diffing on both branches; **response-contract parity** so the OmniScript itself doesn't change; a monitored ramp with defined abort criteria; a **rehearsed** rollback, not a theoretical one; and clarity on what happens to in-flight submissions at the moment of the switch. On the flag: a good architect argues for it (a flag makes rollback seconds instead of a deployment, and enables per-user canary), states the cost, then respects the decision if overruled.

**Strong signals:** Asks about **in-flight work at cutover** — most people miss it entirely. Insists rollback be rehearsed. Defines abort criteria numerically, not "if it looks bad."

**🚩 Red flags:** Accepts with no conditions. Or refuses to proceed without the flag — inflexible.

---

# Scorecard

| Dimension | 1–5 | Evidence |
|---|---|---|
| Diagnoses at volume with real instrumentation (S1, S2, S3) | | |
| Ranks governor limits correctly; knows what's uncatchable (S2, S3) | | |
| Idempotency & recovery thinking (S5, S7, S8) | | |
| Concurrency & locking depth (S6) | | |
| Reads systems, not just code — history, smells, trade-offs (S4, L1) | | |
| AI as engineered workflow with gates (A1, A2, A3) | | |
| Code-review sharpness (A6 finding count: ___ / 10) | | |
| Leadership & cutover judgment (L1, L2) | | |
| Intellectual honesty about limits (A5) | | |

**Hire signal:** collapses per-member rating to per-class in S2 · spots the 131KB Long Text cap in S3 · says "upsert on the External Id, stop branching on a query" in S7 · catches idempotency and partial-success in A6 · has a real false-positive story in A3.

**Concern signal:** architecture spoken only in layers and patterns with no numbers or war stories · reaches for retry before removing the cause · AI answers that stop at "it writes the code for me" · no example of being wrong.
