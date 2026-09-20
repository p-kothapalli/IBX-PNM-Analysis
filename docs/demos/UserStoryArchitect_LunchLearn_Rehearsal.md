# Rehearsal Doc — User Story Solution Architect (AI Lunch & Learn)

**Event:** FY27 REG SolCon AI Lunch & Learn · Fri Jul 17, 12:00–12:30 (recorded)
**Format:** ~18-min talk + ~10-min Q&A · slide deck is the `user-story-architect-demo` canvas
**Goal of the demo:** prove the skill produces build-ready stories AND that it is vertical-agnostic
(one PNM/existing run, one Life Sciences/greenfield run).

> **Golden rule for the live demo:** paste the canned prompt, then **narrate every step**
> (the session is recorded for offline viewers). If a live run stalls, fall back to the
> pre-recorded clip or the "Expected output" blocks below shown on screen.

---

## Speaker intro (~30 sec — say this first)

Hi, I'm **Prashanth Kothapalli**, a **Senior Solution Architect** in **Salesforce Professional
Services (CSG, AMER)**, focused on **Health & Life Sciences**. Over ~7 years here I've grown from
developer to solution architect, delivering Salesforce Industries / OmniStudio and Health Cloud
programs — currently the Independence Blue Cross provider-network build — and I hold 8+ Salesforce
certifications (including Agentforce Life Sciences Consultant, Agentforce Specialist, and OmniStudio
Developer).

> **Bridge line into the demo:** *"A lot of my day is turning fuzzy feature asks into build-ready
> stories — so I built an AI Solution Architect skill to do exactly that, for any Salesforce
> vertical. Let me show you."*

---

## Pre-flight checklist (run ~30 min before)

- [ ] MCP auth live: `code-review-graph` (Scenario A verification) and `git-soma` — tokens expire ~daily; re-auth if needed.
- [ ] Open the [demo deck canvas](/Users/pkothapalli/.cursor/projects/Users-pkothapalli-Documents-IBXQA-IBXQA/canvases/user-story-architect-demo.canvas.tsx) beside the chat.
- [ ] Both canned prompts copied into a scratch note (don't type live).
- [ ] Pre-recorded backup clips of both runs ready.
- [ ] These two "Expected output" stories open in tabs as a visual fallback.
- [ ] Life Sciences knowledge source bookmarked: [Salesforce Life Sciences Librarian (NotebookLM)](https://notebooklm.google.com/notebook/55caac49-5167-4731-bc4f-e1369a88030e).

---

## SCENARIO A — Existing PNM project (≈4 min)

### The prompt (paste verbatim)

```
Write a user story: add a "rush-review reason" field to the Provider Change form
so a PDM Specialist can flag a submission for expedited review, and the reason is
visible downstream on the Case Manager. This is an enhancement to the existing
PNM Provider Change flow. Priority P1.
```

### What to narrate as it runs

1. **Vertical + mode detection** — it recognizes PNM + "enhancement to existing" → Refactor-ish flow, skips the vertical question, and confirms it loaded PNM context.
2. **Question-first** — it asks a small, focused `AskQuestion` set (see below) instead of guessing. Call this out: *"notice it won't invent requirements."*
3. **Graph-first verification** — it runs `code-review-graph:semantic_search_nodes` for the Provider Change OmniScript and its feeding DataRaptor/IP, rather than naming them from memory. *"This is the anti-hallucination guard."*
4. **Output** — a story in the canonical format: concrete persona, GWT ACs in business language, a Technical Implementation table, Definition of done, Estimated Effort.

### Clarifying questions it should ask (rehearse the answers)

| # | Question | Demo answer to give |
|---|----------|---------------------|
| 1 | Which Provider Change form/flow — the OmniScript guided flow, or the PDM Manual variant? | The guided OmniScript flow |
| 2 | Should "rush-review reason" be free text or a restricted picklist? | Restricted picklist |
| 3 | Is the field required only when an "expedited" checkbox is set, or always optional? | Required only when expedited is checked |
| 4 | Where downstream must it be visible — Case Manager record, QC review screen, or both? | Case Manager record (this story), QC screen later |

> If short on time, answer 1–2 live and say "I'll let it put the rest in the Clarification Questions table" — which demonstrates that behavior too.

### Expected output (target shape — component names are graph-verified live)

```markdown
# USER STORY: Rush-Review Reason on the Provider Change Form

**Persona:** PDM Specialist
**Priority:** P1
**OmniScript:** PRM_ProviderChange_English  *(verify exact API name via code-review-graph at runtime)*
**Integration Procedures:** PRM_ProviderChangeSave_Procedure  *(verify)*
**Relevant Requirements:** Provider Change flow (existing)

## Story
**As a** PDM Specialist,
**I want** to flag a Provider Change submission with a rush-review reason,
**So that** expedited cases are prioritized and the reason is auditable on the Case Manager.

**Why it matters:** Time-sensitive provider changes (e.g., termination corrections) currently
have no in-flow way to signal urgency, so they queue behind routine work.

## Acceptance Criteria

**AC-1 — Specialist flags a submission for expedited review**
**Given** a PDM Specialist is completing the Provider Change form and marks the submission as expedited,
**When** they select a rush-review reason and submit,
**Then** the submission is recorded as expedited with the chosen reason,
**And** the reason is shown on the resulting Case Manager record.

**AC-2 — Reason is required only when expedited (edge/negative)**
**Given** a PDM Specialist has NOT marked the submission as expedited,
**When** they submit the form,
**Then** the rush-review reason is optional and submission proceeds normally.

**AC-3 — Expedited without a reason is blocked (edge/negative)**
**Given** a PDM Specialist marks the submission as expedited but leaves the reason blank,
**When** they attempt to submit,
**Then** the form blocks submission and prompts for a rush-review reason.

## Technical Implementation (high-level)
| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_RushReviewReason__c` | New custom field (Picklist) on the Case Manager (IndividualApplication) | Store the selected reason | Drives AC-1 |
| `PRM_IsExpedited__c` | New custom field (Checkbox) | Expedited flag | Drives AC-1/AC-2 |
| `PRM_ProviderChange_English` | Modified OmniScript step | Add expedited checkbox + conditional required picklist | Drives AC-1/AC-3 |
| Provider Change save IP/DR | Modified step | Map new fields onto the Case Manager | Verify name via graph |

## Definition of done
- [ ] Expedited + reason persists to the Case Manager and is visible there (AC-1).
- [ ] Non-expedited submissions unaffected (AC-2).
- [ ] Expedited-without-reason is blocked in-flow (AC-3).
- [ ] New fields deployed with FLS on PDM/QC permission sets.
- [ ] No regression to the existing Provider Change save path.

## Clarification Questions (Before Implementation)
| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Final picklist values for rush-review reason? | Picklist config + validation | BA / Ops |
| 2 | Should QC screen surface the flag now or in a follow-up story? | Scope boundary | Product |

## Estimated Effort  *(AI-estimated — validate with team)*
| Component | Change Type | Effort | Notes |
|---|---|---|---|
| 2 custom fields + FLS | Config | S | Picklist + checkbox |
| OmniScript step | OmniScript element | M | Conditional required logic |
| Save IP/DR mapping | IP/DR step | M | Map to Case Manager |

**Total Estimated Effort:** ~M–L
```

**Talking point to land:** *"A developer could start this now — persona, verifiable ACs, the exact components, and a size. No follow-up meeting."*

---

## SCENARIO B — Greenfield Life Sciences Cloud, pharma (≈4 min)

> This is the agnostic proof. **Different vertical selected, no existing codebase.** Watch that
> zero PNM assumptions leak in, and that with nothing to verify it **proposes** a design and
> **flags** every unknown rather than hallucinating.

### The prompt (paste verbatim)

```
Write a user story for a GREENFIELD Salesforce Life Sciences Cloud implementation
at a pharma company: enroll a patient into a Patient Support Program (PSP), capturing
the patient's consent before enrollment is active. There is no existing codebase yet —
propose the components. Priority P1.
```

### What to narrate as it runs

1. **Vertical switch** — it selects **Life Sciences / Health Cloud**, not PNM. Persona and object model change accordingly (Patient Services Coordinator; CareProgram/consent objects, not PRM_/IndividualApplication).
2. **Greenfield behavior** — it notes there's no repo to verify against, so component names are **proposed** and every assumption becomes a **Clarification Question**. *"Same discipline, but it degrades gracefully — exactly what an SA does on day one of a new build."*
3. **Standard-object grounding** — for standard Health Cloud/LSC objects it can lean on Salesforce docs / the Life Sciences Librarian, not the PNM graph.

### Clarifying questions it should ask (rehearse the answers)

| # | Question | Demo answer to give |
|---|----------|---------------------|
| 1 | Is the patient a Person Account or a Contact under a Household/Account? | Person Account |
| 2 | Which consent model — documented authorization form, or channel consent (call/text/email)? | Documented authorization form consent |
| 3 | Must consent be captured before enrollment becomes Active, or can enrollment be Pending until consent? | Enrollment stays Pending until consent is captured |
| 4 | In scope now: manual coordinator entry, or also self-service/portal enrollment? | Manual coordinator entry only for this story |

### Expected output (target shape — greenfield, components PROPOSED)

```markdown
# USER STORY: Enroll a Patient into a Patient Support Program with Consent Capture

**Persona:** Patient Services Coordinator
**Priority:** P1
**OmniScript:** [PROPOSED] PSP_PatientEnrollment_English (greenfield — to be built)
**Integration Procedures:** [PROPOSED] PSP_EnrollPatient_Procedure
**Relevant Requirements:** New PSP program build (no prior story)

## Story
**As a** Patient Services Coordinator,
**I want** to enroll a patient into a Patient Support Program and capture their consent,
**So that** the patient can begin receiving program services only after valid consent is on file.

**Why it matters:** Pharma PSPs must not deliver services (co-pay, adherence, nursing support)
before documented patient consent — enrolling without it is a compliance risk.

## Acceptance Criteria

**AC-1 — Coordinator enrolls a patient (happy path)**
**Given** a Patient Services Coordinator has an eligible patient record,
**When** they complete the enrollment form and capture the patient's signed authorization,
**Then** the patient is enrolled in the program,
**And** the enrollment becomes Active only once consent is recorded.

**AC-2 — Enrollment without consent stays Pending (edge)**
**Given** a coordinator submits an enrollment but consent has not yet been captured,
**When** they save,
**Then** the enrollment is created in a Pending state,
**And** no program services are triggered until consent is recorded.

**AC-3 — Expired or declined consent blocks activation (negative)**
**Given** a patient's authorization is declined or past its valid date,
**When** the coordinator attempts to activate the enrollment,
**Then** activation is blocked with a clear reason,
**And** the enrollment remains Pending.

## Technical Implementation (high-level)
> Greenfield — components are PROPOSED against standard LSC/Health Cloud objects
> (validate against the Life Sciences Librarian + Salesforce docs before build).

| Component | Type | Change | Notes |
|---|---|---|---|
| `CareProgram` | Standard object | Represents the PSP | Config the program record |
| `CareProgramEnrollee` / `ProgramEnrollment` | Standard object | The patient's enrollment + status | Pending → Active on consent |
| `AuthorizationFormConsent` | Standard object | Documented consent record | Gates activation (AC-1/AC-3) |
| [PROPOSED] `PSP_PatientEnrollment_English` | New OmniScript | Coordinator-guided enrollment + consent step | Drives AC-1/AC-2 |
| [PROPOSED] `PSP_EnrollPatient_Procedure` | New Integration Procedure | Create enrollment, link consent, set status | Drives AC-1/AC-3 |

## Definition of done
- [ ] Patient enrolls and enrollment activates only after consent (AC-1).
- [ ] No-consent enrollment persists as Pending; no services fire (AC-2).
- [ ] Declined/expired consent blocks activation with a reason (AC-3).
- [ ] Consent record linked to the enrollment and auditable.

## Clarification Questions (Before Implementation)
| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Confirm patient = Person Account vs. Contact | Data model foundation | Solution Architect |
| 2 | Which standard consent object fits the authorization model (AuthorizationFormConsent vs. ContactPointConsent)? | Compliance design | Legal / SA |
| 3 | Program services trigger mechanism (Flow, IP, platform event)? | Downstream design | SA |
| 4 | Self-service/portal enrollment in a later phase? | Scope roadmap | Product |

## Estimated Effort  *(AI-estimated — validate with team)*
| Component | Change Type | Effort | Notes |
|---|---|---|---|
| CareProgram + enrollment config | Config | M | Standard object setup |
| Consent object + linkage | Config/Data model | L | Compliance-sensitive |
| Enrollment OmniScript | New OmniScript | XL | Guided flow + consent step |
| Enroll IP | New IP | XL | Status + consent gating logic |

**Total Estimated Effort:** ~XL (greenfield foundation)
```

**Talking point to land:** *"Same skill, a pharma story — Patient Services Coordinator, CareProgram, consent gating. Not one PNM term leaked in. That's what 'Solution Architect for any Salesforce project' means."*

---

## Side-by-side close (use on the Agnostic / Close slide)

| Dimension | Scenario A (PNM, existing) | Scenario B (LSC pharma, greenfield) |
|---|---|---|
| Persona | PDM Specialist | Patient Services Coordinator |
| Object model | IndividualApplication (Case Manager), PRM_ fields | CareProgram, ProgramEnrollment, AuthorizationFormConsent |
| Component naming | `PRM_ProviderChange_English` (verified in graph) | Proposed OmniScript/IP (flagged, no repo) |
| Grounding | code-review-graph verification | Salesforce docs + Life Sciences Librarian |
| Unknowns | Small clarification table | Larger clarification table (greenfield) |
| Same contract | Persona · GWT ACs · Tech-Impl · DoD · Effort | Persona · GWT ACs · Tech-Impl · DoD · Effort |

**One-liner:** *The discipline is identical; only the knowledge pack changed.*

---

## Timing crib (keep the demo on rails)

| Segment | Budget | Hard stop |
|---|---|---|
| Scenario A run + narration | 4:00 | If graph call is slow, cut to expected-output tab |
| Scenario B run + narration | 4:00 | If it over-asks questions, answer 2 and jump to output |
| Buffer | — | If both run long, skip AC-3 read-through in each |
