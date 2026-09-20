# Interactive Lifecycle Mind-Map — Generation Prompt (Reusable)

**Purpose:** A single, reusable prompt that turns the analysis in `requirements/` into a
self-contained, interactive **HTML mind map** of a flow's end-to-end life cycle. The first
target is the **Practitioner Participation (PAR) Form**, but the same prompt is meant to be
re-run for Recredentialing PDA, PSV "Add a Location", Off-Cycle, Ancillary, etc.

---

## The prompt

> **Build a single self-contained HTML file** (no external CDNs, no build step — inline CSS +
> vanilla JS only, so it opens by double-clicking) that visualizes the **end-to-end life cycle
> of `<FLOW NAME>`** as an **interactive, clickable mind map**.
>
> **Source of truth:** Use only the analysis already captured in this repo's `requirements/`
> folder (and the codebase when a doc points to a specific OmniScript / IP / DataRaptor / Apex
> class). Do **not** invent steps. Every node's detail must be traceable to a requirement doc,
> a defect/QA bug number, or a named metadata component. Cite the source doc filename in each
> node's detail.
>
> **Structure the content as a hierarchy** with a single root node (`<FLOW NAME> Life Cycle`)
> and one branch per **life-cycle phase**, in chronological order. Under each phase, add child
> nodes for the discrete steps / processes / decisions / records that happen in that phase.
>
> **Each node carries rich, structured detail** rendered in a side panel when clicked:
> - `summary` — one or two plain-language sentences: what happens here and why.
> - `rules` — the business / validation rules that govern this node (show conditions, hard
>   blocks, required fields, branching logic). Quote exact element names and expressions where
>   the doc gives them.
> - `components` — the concrete Salesforce metadata involved (OmniScript step/element names,
>   Integration Procedures, DataRaptors, Apex classes, LWCs, objects/fields).
> - `records` — any records created/updated at this node, in sequence, with the key fields set.
> - `gotchas` — known defects, edge cases, partial-data risks, QA bug numbers, "not yet live"
>   notes. Flag severity.
> - `source` — the requirement doc(s) this node is derived from.
>
> **Visual style — Lucid-style flow diagram (not a tree):**
> Render the life cycle as a **top-to-bottom flowchart on a dotted canvas**, matching the look
> of a Lucid/Visio process diagram:
> - A **vertical main spine** of the primary phases connected by **orthogonal connector arrows**
>   (SVG, with arrowheads).
> - **Flowchart shapes by node kind**: terminator/pill for Start & End, rounded rectangle for
>   steps/processes, **diamond** (clip-path) for decisions, **parallelogram** for data/records.
> - **Decision branches** drawn as labeled edges (e.g. `Yes` / `No`, `Approve` / `Deny`) — the
>   spine continues on the primary outcome; the alternate outcome branches to a side box.
> - **Side callouts on the right lane**: record-creation detail boxes and **red defect callouts**
>   (dashed red connectors) hang off the specific step they affect.
>
> **Interaction & UX requirements:**
> 1. Clicking any box opens a **detail panel** (right side) with the structured content above,
>    formatted into labeled sections. Only render sections that have content. The panel also
>    lists child nodes as clickable "Drill into" links.
> 2. **Zoom controls** (in / out / fit) and a scrollable/pannable canvas.
> 3. A **search box** that highlights matching boxes and dims the rest.
> 4. **Legend + color coding by node kind**: `phase` (start/end), `step` (user UI step),
>    `process` (system/async), `decision`, `record`, `defect`.
> 5. A **"highlight defects"** filter and a **reset** control.
> 6. Fully responsive; readable on a laptop; print-friendly (so it can be exported to PDF).
> 7. Modern, clean styling in an IBX-style blue palette. No emojis in the UI chrome.
> 8. **Multi-flow shell with a left sidebar.** The page hosts *many* guided flows (PAR Form,
>    Off-Cycle, Recred PDA, PSV, Ancillary, …). A left sidebar lists every flow (name +
>    subtitle + the OmniScript/meta line); clicking one swaps the canvas + detail panel.
>    Adding a flow = appending one object to the top-level `FLOWS` array — no other code change.
> 9. A single top-level `FLOWS` array at the top of the `<script>`. Each entry is
>    `{ id, name, subtitle, meta, detail, flow }` where `detail` is the cited content tree
>    (root `id:"root"`, ids may repeat across flows since `byId` is rebuilt per active flow)
>    and `flow` is the ordered diagram spine + side callouts referencing detail by id. The
>    engine (`buildFlow`, `layout`, `renderDetail`, zoom/search) is flow-agnostic and reused.
>
> **Deliverable:** one `.html` file under `requirements/Visualizations/`, named
> `<FLOW>_Lifecycle_MindMap.html`. Open-by-double-click must work offline.

---

## Node detail schema (the JS data contract)

```js
{
  id: "unique-kebab-id",
  title: "Human readable title",
  kind: "phase|step|process|decision|record|defect",
  summary: "1–2 sentence plain-language description.",
  rules:      ["rule or validation 1", "rule 2", ...],      // optional
  components: ["PRM_SomeOmniScript : ElementName", "PRM_SomeIP", ...], // optional
  records:    ["Location (seq 1): Name, LocationType, PRM_Pending__c=true", ...], // optional
  gotchas:    ["QA Bug 1216121 (HIGH): ...", ...],          // optional
  source:     ["Some_Requirement_Doc.md"],                   // optional
  children:   [ ...same shape... ]                            // optional
}
```

## Reuse checklist (per new flow)

- [ ] Identify the canonical OmniScript / entry point and list its steps in order.
- [ ] Map the submit → record-creation IP/DR chain and the records it writes.
- [ ] Capture the downstream credentialing stages (App Review → PSV → QC → Committee →
      Decision → Activation) that the created case flows into.
- [ ] Pull all known defects / "not yet live" items into a cross-cutting `defect` branch and
      also annotate them on the specific node they affect.
- [ ] Cite the source doc in every node.
