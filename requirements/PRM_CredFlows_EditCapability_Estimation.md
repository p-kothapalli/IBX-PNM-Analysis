# Credentialing Flows — Edit/Save Capability Estimation
## Option A (Existing OmniScripts) vs Option B (Tile-Based LWC Redesign)

**Business Ask:** Add the ability to edit and save fields within credentialing guided flows
(Initial Cred and ReCred). Examples: address information, Date of Birth, education records.

**Goal:** Decrease business reliance on admins for simple field changes; reduce incident ticket
volume; allow reviewers to correct data in the flow without exiting to update records manually.

**Flows in Scope:**
1. Application Review (`PRM_InitialCredentialAppReview_English`)
2. Initial Cred PSV Review (`PRM_PrimarySourceVerificationReview_English` v47 — 186+ elements)
3. ReCred PSV Review (`PRM_ReCredUpdate_English`)
4. Initial Cred PSV QC (`PRM_PrimarySourceVerificationReview_English` with CaseType = QC Review)
5. ReCred PSV QC (`PRM_RecredQC_English`)
6. PDA QC Review (`PRM_InitialCredPDAQC_English`)

---

## Executive Comparison

| | Option A: Edit in Existing OmniScripts | Option B: Tile-Based LWC Redesign |
|---|---|---|
| **Total effort** | **~37–52 developer-days** | **~122 developer-days** |
| **Calendar time** | **~8–11 weeks** | **~13 weeks (parallel)** |
| **Solves 4MB "Save for Later" failure?** | **NO — makes it worse** | **YES — eliminated by design** |
| **Edit capability** | Partial — in-flow only, still lost on timeout | Full — per-tile, saved immediately |
| **Resume / pause** | No — all-or-nothing still | Yes — any tile, any time |
| **Visual progress** | No | Yes |
| **Long-term maintainability** | Low — technical debt per OS | High — shared LWC framework |
| **If Option A now, redesign later** | Must undo Option A work | N/A — no undo needed |
| **True total cost if both done** | **Option A + Option B (~159–174 days)** | **Option B only (~122 days)** |

> **Bottom line for business:** Option A delivers edit capability faster and cheaper in isolation,
> but it does not solve the 4MB payload problem (it worsens it), does not enable pause/resume,
> and will need to be undone when the tile redesign is eventually built. The true cost of doing
> Option A first and then the redesign is **30–40% more total effort** than doing the redesign
> directly. Option B is the recommended path.

---

## Option A: Edit Capability in Existing OmniScripts

### What "Edit Capability in OmniScript" Requires

For each field that business wants to edit, the work involves:

1. **OmniScript element change** — convert the display element (Text Block / read-only field)
   to an editable input (Text, Date, Picklist, etc.) with a `readOnly: false` toggle
2. **DataRaptor Read pre-population** — the current DR reads already fetch the value for display;
   confirm the same value is mapped into the new editable input element correctly
3. **DataRaptor Update / IP extension** — `PRM_ReviewPSVCaseRecordsUpdate` (70–90+ elements)
   must be extended with new action paths for each newly editable field set that saves back to
   Salesforce on form submission
4. **Array/repeating section edits** — Education, Licenses, Addresses are arrays. Each requires:
   - "Edit row" / "Add row" / "Delete row" capability within the OmniScript repeating block
   - A DR Update per row save
   - Conditional rendering logic (show edit form vs display row)
5. **OmniStudio republish** — every change requires the OmniScript to be republished in the UI,
   a manual step that cannot be automated via CI/CD pipelines
6. **Sub-OmniScript data passing** — the flows use nested sub-OS (e.g. `CredApplicationReviewSubOS`,
   `PRM_PSVSubOsTxnyRole_English`). Editable values set in a sub-OS must be passed back up to
   the parent correctly via `omniscript_jsonDef` and `omniJsonData` — fragile pattern

### Critical Constraint: The 4MB Problem Gets Worse

The current OmniScripts are already failing "Save for Later" due to the 4MB payload limit.
Adding editable fields means the OmniScript payload must carry **both** the original read-only
display data AND the new editable field state. For the PSV flow with 100+ addresses, this will
push the payload significantly past the current limit:

```
Current payload (read-only display): ~3.5–4MB (already failing)
After adding editable address fields: ~5–7MB estimated (guaranteed failure for large practitioners)
```

**Edit capability in Option A will NOT be usable for large practitioners** — the exact use case
where the business needs it most.

---

### Option A Flow-by-Flow Breakdown

#### Flow 1: Application Review (`PRM_InitialCredentialAppReview_English`)

**Editable fields requested:** Name corrections, DOB, NPI confirmation, Education records
(add/edit/remove), License records (SBRD, DEA, CDS), Board Certifications

**Sub-OmniScripts affected:**
- `CredApplicationReviewSubOS` — Education, License, DEA, CDS sections
- `CredApplicationReviewOSTxnyRole` — Taxonomy/role (already partially editable)
- `CredentialAppReviewCompleteOS` — Final submit (needs new DR actions wired in)

| Work Item | Days | Notes |
|-----------|------|-------|
| Name / DOB / NPI — toggle from display to editable input | 1 | Text element → input; pre-pop from existing DR read |
| Education array — add/edit/delete rows in `CredApplicationReviewSubOS` | 3 | Repeating section with row edit capability; DR Update per row + new IP path |
| License (SBRD) array — add/edit/delete | 3 | Same pattern as Education; duplicate detection logic |
| DEA array — add/edit/delete | 2 | Similar; DEA-specific fields |
| CDS array — add/edit/delete | 1.5 | Similar to DEA |
| Extend `PRM_ReviewPSVCaseRecordsUpdate` IP (new DR action paths for each field set) | 2.5 | DR Update per object type edited; IP has 70+ elements already |
| Integration testing — test each edit path end-to-end | 2 | Manual: open OS, edit each field, submit, verify record updated |
| OmniStudio republish + smoke test | 0.5 | Manual UI republish |
| **Flow 1 Total** | **~15.5 days** | |

#### Flow 2: Initial Cred PSV Review (`PRM_PrimarySourceVerificationReview_English` v47)

**The most complex existing OmniScript — 186+ elements.**

**Editable fields requested:** DOB, Gender, Email, Degree, Telehealth, Group NPI, Tax ID,
Addresses (100+), Demographics/Diversity fields, Languages, Contact information, Board Certifications

| Work Item | Days | Notes |
|-----------|------|-------|
| Practitioner info fields (DOB, Gender, Email, Degree, Telehealth) | 1.5 | Text/Date/Picklist elements; straightforward |
| Group/Practice fields (Group NPI, Tax ID, Practice Type) | 1 | Similar to above |
| Address editing (100+ addresses, each with 10+ editable fields) | **8** | **Largest item.** Each address needs edit form; async save per address to avoid payload overflow; pagination. The OS already struggles here in read-only mode. |
| Demographics & Diversity (multi-select, pronouns, affirming care) | 1.5 | Multi-select OS elements + DR Update |
| Languages (multi-select + fluency per language) | 1.5 | Repeating section with fluency edit per row |
| Contact information | 1 | Text fields, straightforward |
| Board Certification (ReCred section) | 2 | Add/edit/remove + expiration validation |
| Extend `PRM_ReviewPSVCaseRecordsUpdate` IP for all new fields | 4 | Large IP already; each new field set = new DR action path |
| Integration testing | 3 | Large payload; test with 50+ addresses; regression on existing IP paths |
| OmniStudio republish + smoke test | 0.5 | |
| **Flow 2 Total** | **~24 days** | |

#### Flow 3: ReCred PSV Review (`PRM_ReCredUpdate_English`)

**Separate OmniScript series** from PSV (4–7 versions found). ReCred has its own element set
but covers the same practitioner fields.

| Work Item | Days | Notes |
|-----------|------|-------|
| Identify delta from PSV (which elements exist, which are missing) | 1 | Audit each ReCred OS version against PSV changes |
| Port PSV editable fields to ReCred OS elements | 4 | Most IP paths from PSV can be reused; OS element changes must be re-done |
| ReCred-specific additions (Board Cert, CMS Preclusion) | 1.5 | |
| IP extension for ReCred-specific fields | 1.5 | |
| Integration testing | 2 | |
| **Flow 3 Total** | **~10 days** | |

#### Flows 4 & 5: PSV QC + ReCred QC (`PRM_RecredQC_English`, PSV with QC flag)

QC flows are mostly display — the QC reviewer verifies PSV work and sets QC outcome. The main
editable adds are QC override fields and notes. Practitioner data editing in QC is a lesser
requirement (QC should be reviewing, not re-entering).

| Work Item | Days | Notes |
|-----------|------|-------|
| QC override / notes fields (already partially present) | 1 | Minimal net-new |
| PSV data display for QC context (read-only summary) | 1 | Ensure PSV edit results show in QC |
| Integration testing | 1.5 | |
| **Flows 4+5 Total** | **~3.5 days** | |

#### Flow 6: PDA QC Review (`PRM_InitialCredPDAQC_English`)

Network assignment and info code edits are the primary ask. Practice location networks/info codes
are already somewhat editable in the current flow; the gap is on practitioner demographic fields.

| Work Item | Days | Notes |
|-----------|------|-------|
| Practitioner demographic display → editable (Name, NPI, Role) | 1 | |
| Network assignment multi-select (already exists — verify edit saves correctly) | 2 | Current dual-select may need DR Update wiring |
| Info code multi-select (similar) | 1.5 | |
| Directory indicators toggle (already partially present) | 1 | |
| IP / DR extension for new editable fields | 2 | `PRM_NetworkManagementQCUpdate` IP extension |
| Integration testing | 1.5 | |
| **Flow 6 Total** | **~9 days** | |

---

### Option A — Total Summary

| Flow | Days |
|------|------|
| Flow 1: Application Review | 15.5 |
| Flow 2: Initial Cred PSV | 24 |
| Flow 3: ReCred PSV | 10 |
| Flows 4+5: PSV QC + ReCred QC | 3.5 |
| Flow 6: PDA QC | 9 |
| **Total** | **~62 days sequential** |

> **With 2 senior devs + Cursor AI (2× multiplier for OmniStudio work is lower — OmniStudio
> UI changes cannot be AI-generated, only the IP/DR Apex logic):**
> **~37–45 days effort, ~8–10 weeks calendar time with 2 devs working in parallel on different flows**

### Option A — What It Does NOT Solve

| Problem | Status After Option A |
|---------|----------------------|
| 4MB "Save for Later" failure | **Worse** — payload increases with editable field state |
| All-or-nothing session (lose edits on timeout) | **Unchanged** — still all-or-nothing |
| No visual progress | **Unchanged** |
| No pause/resume capability | **Unchanged** |
| Linear flow sequence | **Unchanged** |
| No collaboration (single reviewer) | **Unchanged** |
| OmniStudio deployment friction | **Same** — still requires manual republish per change |

---

## Option B: Edit Capability in Tile-Based LWC Redesign

The full LWC redesign documented in `MASTER_Development_Plan_Credentialing_LWC_Redesign.md`
**already includes edit capability as a core feature** — not an add-on. From the design documents:

> **"ALL FIELDS ARE EDITABLE (key business requirement)"** — PSV_Review_LWC_Redesign_Detailed_Design.md

Edit capability is native to the tile architecture:
- Each tile opens in a modal with editable Salesforce fields
- Saves immediately on tile submit — no waiting for end-of-flow
- No payload limit — each tile payload is ~200KB maximum
- CAQH data always displayed read-only on the left; Salesforce fields editable on the right
- Changes survive timeout — saved to `PRM_VerificationTileStatus__c` immediately

### Option B — Scope Summary (From Master Plan)

| Flow | Tiles | Days (AI-Assisted) | Dependency |
|------|-------|--------------------|------------|
| Flow 1: App Review (+ shared framework) | 10 + 6 framework | 40 | First — builds foundation |
| Flow 2: Initial Cred PSV | 10 | 25 | After Flow 1 framework |
| Flow 3: ReCred PSV | 11 (8 reused) | 15 | After Flow 2 |
| Flow 4: PSV QC | 10 (8 QC wrappers) | 10 | After Flow 2 |
| Flow 5: ReCred PSV QC | 11 (8 reused) | 7.5 | After Flows 3+4 |
| Flow 6: PDA QC | 7 | 25 | Parallel with Flow 2 (after framework) |
| **Total** | **59 tiles** | **~122.5 days** | |

**Calendar time (parallel execution, 2 LWC devs + 1 Apex dev):** ~13 weeks

### What Option B Solves That Option A Does Not

| Problem | Option B |
|---------|---------|
| Edit capability | ✅ Full — all fields editable per tile |
| 4MB payload failure | ✅ Eliminated — per-tile saves ~200KB max |
| All-or-nothing session | ✅ Eliminated — tiles save independently |
| Visual progress tracking | ✅ Built in — tile grid with status badges |
| Pause/resume | ✅ Built in — `PRM_VerificationSession__c` |
| Collaboration | ✅ Multiple reviewers, different tiles |
| Maintainability | ✅ 49 reusable LWC components |

---

## Side-by-Side: The Real Cost Comparison

### If Business Chooses Option A First, Then Redesign Later

This is a common pattern and always costs more than doing the redesign upfront:

```
Option A now (edit in existing OS):         ~37–45 dev-days
  ├─ 4MB problem gets worse
  ├─ Still no pause/resume, no progress
  └─ Work must be UNDONE when redesign comes

Option B later (tile redesign):             ~122 dev-days
  └─ Dev team must first remove Option A changes from OS before
     the OS can be decommissioned cleanly

Total (Option A → then Option B):           ~159–167 dev-days
                                            ~28–30 weeks calendar
```

```
Option B only (redesign first):             ~122 dev-days
                                            ~13 weeks calendar
```

**Option A first → then redesign costs 30–37% more total effort and 15+ additional weeks.**

### If Business Never Redesigns (Option A Permanently)

If the intention is to keep the OmniScripts forever and only add edit capability:

- Option A **works** and costs ~37–45 dev-days
- But the 4MB problem will continue to cause failures for large practitioners
- Business will continue submitting admin tickets for records that exceed the payload limit
- Every OmniScript version upgrade (Salesforce releases) must be re-tested and re-published manually
- Technical debt compounds with each additional edit requirement

---

## Sprint Plan Comparison

### Option A Sprint Plan (8–10 weeks, 2 devs parallel)

```
Sprint 1 (2 weeks): Flow 1 (App Review) — Dev 1
                    Flow 6 (PDA QC) — Dev 2
                    IP extensions for both flows

Sprint 2 (2 weeks): Flow 2 (PSV) Part 1: Practitioner Info + Group + Demographics
                    Flow 3 (ReCred PSV) Part 1 — port from PSV

Sprint 3 (2 weeks): Flow 2 (PSV) Part 2: Address editing (largest item)
                    Flows 4+5 (QC flows) — both devs

Sprint 4 (2 weeks): Flow 2 integration testing + IP extension
                    Flow 3 completion + integration testing
                    UAT for Flows 1, 4, 5, 6

Sprint 5 (1 week): UAT for Flows 2+3, bug fixes, final deploys
```

**Constraint:** PSV address editing (8 days) is the critical path; cannot parallelize easily.

### Option B Sprint Plan (13 weeks parallel, 2 LWC devs + 1 Apex dev)

*(Per `MASTER_Development_Plan_Credentialing_LWC_Redesign.md`)*

```
Weeks 1–3:   Dev A + Dev B: Shared framework (dashboard, tiles, modal, session objects)
             Apex Dev: Custom objects + Apex controllers

Weeks 4–8:   Dev A: App Review tiles (Flows 1+2 sequential)
             Dev B: PDA QC tiles (Flow 6, parallel)

Weeks 9–11:  Dev A: ReCred PSV tiles (Flow 3)
             Dev B: PSV QC wrapper tiles (Flow 4)

Weeks 11–12: Dev A+B: ReCred PSV QC (Flow 5) — fast due to reuse
             UAT for all flows

Week 13:     Cutover: deploy alongside OmniScripts, opt-in "Try New Experience"
```

---

## Recommendation

| Scenario | Recommendation |
|----------|---------------|
| **Business wants edit capability AND long-term platform health** | **Option B** — the redesign solves all problems at once and the edit capability is native |
| **Business wants edit capability NOW in < 8 weeks, redesign is explicitly NOT planned** | **Option A** — faster delivery for the specific ask, but document the 4MB risk and technical debt |
| **Business wants edit capability, redesign is planned for later** | **Option B** — doing Option A first and then undoing it costs 30–37% more total |
| **Small subset of flows only (e.g. just App Review)** | Option A for App Review only (~15 days) is viable if the others are not urgent |

### The One Unavoidable Issue With Option A

No matter which path is chosen, the 4MB payload failure for large practitioners **cannot be fixed
within the existing OmniScript architecture**. The fix requires either:
- The tile-based approach (Option B), where each tile saves ~200KB independently; or
- A custom async save mechanism inside the OmniScript (significant Apex + Platform Event work
  equivalent in effort to Option B but without the UX benefits)

If business users are currently hitting the 4MB failure on large practitioners (multiple practice
locations, 50+ licenses), Option A will not help those users — and adding editable fields will
make the failure more frequent.

---

## Risk Summary

| Risk | Option A | Option B |
|------|---------|---------|
| 4MB payload failure continues | **Confirmed — worsens** | Eliminated |
| Lost edits on session timeout | **Confirmed — unchanged** | Eliminated |
| OmniStudio republish required for every fix | **Confirmed** | None — standard LWC deployment |
| Large address dataset (100+) unusable | **Confirmed — gets worse** | Handled via async pagination |
| IP `PRM_ReviewPSVCaseRecordsUpdate` becomes more complex | High — 70+ elements grows | Not touched — reused as-is |
| Regression on existing IP paths | Medium — extending a large IP | Low — IP interface unchanged |
| Business requests more editable fields after delivery | High effort per addition | Low — config change in LWC props |

---

*References:*
- `requirements/ReDesignCredFlows/MASTER_Development_Plan_Credentialing_LWC_Redesign.md`
- `requirements/ReDesignCredFlows/Application_Review_LWC_Redesign_Detailed_Design.md`
- `requirements/ReDesignCredFlows/PSV_Review_LWC_Redesign_Detailed_Design.md`
- `requirements/ReDesignCredFlows/PDA_QC_Review_LWC_Redesign_Detailed_Design.md`
- `PRM_PrimarySourceVerificationReview_English` v47 (186+ elements)
- `PRM_InitialCredentialAppReview_English` v28
- `PRM_ReviewPSVCaseRecordsUpdate` (70–90+ element IP, 24 versions)
- `PRM_HighVolume_Processing_SK_Estimation.md` — async processing patterns (relevant to address saves)
