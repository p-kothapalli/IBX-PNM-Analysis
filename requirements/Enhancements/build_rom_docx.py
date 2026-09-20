#!/usr/bin/env python3
"""Build the IBX PIE 2027 Priorities ROM as a formatted Word document.

Content is grounded in requirements/2027_ROM_TDD/00_ROM_TDD_Summary.md and the
per-feature TDD/estimation docs. Run:  python3 build_rom_docx.py
"""

from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ── IBX palette ──────────────────────────────────────────────────────────
IBX_BLUE  = RGBColor(0x00, 0x30, 0x87)
IBX_MED   = RGBColor(0x00, 0x57, 0xB8)
IBX_LIGHT = RGBColor(0x00, 0x9C, 0xDE)
IBX_TEAL  = RGBColor(0x00, 0xB4, 0xC8)
IBX_GREEN = RGBColor(0x00, 0x86, 0x3F)
IBX_ORANGE= RGBColor(0xC0, 0x5A, 0x00)
IBX_RED   = RGBColor(0x99, 0x00, 0x00)
IBX_MUTED = RGBColor(0x5A, 0x70, 0x90)
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)

BLUE_HEX  = "003087"
MED_HEX   = "0057B8"
LIGHT_HEX = "E8F0FA"
GREY_HEX  = "F4F7FB"


# ── low-level helpers ────────────────────────────────────────────────────
def set_cell_bg(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def set_cell_margins(cell, top=60, bottom=60, left=110, right=110):
    tcPr = cell._tc.get_or_add_tcPr()
    m = OxmlElement("w:tcMar")
    for tag, val in (("top", top), ("bottom", bottom), ("start", left), ("end", right)):
        e = OxmlElement(f"w:{tag}")
        e.set(qn("w:w"), str(val))
        e.set(qn("w:type"), "dxa")
        m.append(e)
    tcPr.append(m)


def shade_paragraph(paragraph, hex_color):
    pPr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    pPr.append(shd)


def add_bottom_border(paragraph, size=18, hex_color=BLUE_HEX):
    pPr = paragraph._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), hex_color)
    pbdr.append(bottom)
    pPr.append(pbdr)


def style_table_borders(table, hex_color="D0DFF0", size=4):
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), str(size))
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), hex_color)
        borders.append(e)
    tblPr.append(borders)


def run(p, text, size=11, bold=False, color=None, italic=False, font="Calibri"):
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.name = font
    if color is not None:
        r.font.color.rgb = color
    return r


def heading(doc, text, size=16, color=IBX_BLUE, space_before=14, space_after=6, border=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    run(p, text, size=size, bold=True, color=color)
    if border:
        add_bottom_border(p, hex_color=BLUE_HEX)
    return p


def bullet(doc, label, text, label_color=IBX_MED):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(3)
    if label:
        run(p, label + " ", bold=True, color=label_color, size=10.5)
    run(p, text, size=10.5)
    return p


def para(doc, text, size=10.5, color=None, italic=False, space_after=8, bold=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    run(p, text, size=size, color=color, italic=italic, bold=bold)
    return p


# ── data ─────────────────────────────────────────────────────────────────
FEATURES = [
    {
        "n": 1, "name": "PDM Efficiency + PEAR Provider Self-Service",
        "size": "XL", "conf": "Medium", "ai": "59–73", "base": "84–107",
        "scope": [
            ("", "Balanced internal PDM efficiency + external PEAR self-service."),
            ("", "PEAR: providers add / term locations, networks, and demographics themselves."),
            ("", "PDM: self-serve simple field edits to cut the admin-ticket queue."),
        ],
        "tdd": [
            ("", "PEAR edits update provider records directly — there is no QC review step for PEAR."),
            ("", "Harden community FLS / security and inline validation for provider-facing writes."),
            ("", "Extend existing PEAR OmniScripts + DataRaptors rather than rebuild."),
        ],
        "risk": "Because PEAR writes apply directly (no QC gate), inline validation and a full audit trail are essential to protect data integrity. Only 15 of 192 custom components are community-enabled today, so provider-facing screens carry an enablement cost.",
        "reuse": "Internal PDM bulk edits can leverage the F7 async engine; PEAR updates apply directly.",
    },
    {
        "n": 2, "name": "Credentialing Enhancements — Tiles, CAQH Documents & Agentic AI",
        "size": "XXL", "conf": "Mixed (Tile High / CAQH Low–Med / Agentic Med–Low)", "ai": "211–281", "base": "322–421",
        "scope": [
            ("", "The 5 core credentialing flows re-platformed to the tile experience — a codebase audit counts ~108 steps in those flows (not the ~55 tiles originally assumed)."),
            ("", "Retrieve real CAQH document files — not just structured data."),
            ("", "Agentic AI: Phase 0 foundation + 2 pilot agents (human-in-the-loop)."),
        ],
        "tdd": [
            ("", "Shared tile + session framework across all flows (autosave, resume-anywhere)."),
            ("", "CAQH document API to Salesforce Files + audit linkage."),
            ("", "Einstein Trust Layer, RAG grounding, human-in-loop, and an eval harness."),
        ],
        "risk": "This is a multi-team program, not one feature — the wider credentialing family is 45 OmniScripts / 304 steps, so the '5 flows' boundary must be named before funding. CAQH connectivity already exists (44 CAQH Apex classes + a CAQH named credential); it is the document entitlement that is unverified.",
        "reuse": "The tile framework is reused across all flows and by the mass-update grid (F7).",
    },
    {
        "n": 3, "name": "Enhanced Case Management",
        "size": "L–XL", "conf": "Medium", "ai": "47–68", "base": "68–100",
        "scope": [
            ("", "Smart + configurable case routing and assignment."),
            ("", "Fix the duplicate-QC-case defect; fix queue & owner-change permissions."),
            ("", "Exception / hold tracking + in-case tracker, worklists, and SLA aging."),
        ],
        "tdd": [
            ("", "Idempotent case creation to kill duplicates; skill + workload assignment engine."),
            ("", "Hold / exception model with reason codes and re-entry rules."),
            ("", "SLA aging alerts + supervisor worklist views."),
        ],
        "risk": "Touches the shared review IP write path — meaningful regression surface across credentialing. There are 14 queues but zero assignment rules today, so all routing is code-driven and the configurable engine is genuinely net-new.",
        "reuse": "Routing & worklists are reused by F5 (shared views) and F6 (leadership inventory).",
    },
    {
        "n": 4, "name": "Full Provider Data Versioning",
        "size": "XXL", "conf": "Medium (High Risk)", "ai": "220–270", "base": "475–490",
        "scope": [
            ("", "Effective-dated versioning across the 42 provider objects that are actually written today (the earlier '~30' undercounted)."),
            ("", "Drivers: compliance, point-in-time history, future & back-dated changes."),
            ("", "Pinned-current model with version-up / version-down."),
        ],
        "tdd": [
            ("", "Version state-machine: pinned-current + version down/up + back-date + natural-key error-out."),
            ("", "Point-in-time query API. Phase by tier: Tier 1 = the 14 highest-traffic objects, which carry ~80% of the write path."),
            ("", "Heavy regression harness to protect existing write paths. A partial head start exists — 596 fields are already history-tracked across 53 objects."),
        ],
        "risk": "Regression blast radius measured at 478 write-path Load DataMappers and 236 DML-performing Apex classes across 42 objects — larger than previously stated. 7 business pre-conditions remain open. Strongly recommend funding Tier 1 only in 2027.",
        "reuse": "The versioned write model underpins F5 (no re-entry), F6 (history feeds), and F8 (terminations).",
    },
    {
        "n": 5, "name": "Cred + PDM Integration",
        "size": "L", "conf": "Medium", "ai": "34–52 (net-new)", "base": "50–75 (net) · gross 73–106 / 49–74 AI",
        "scope": [
            ("", "Automated cred to PDM handoff — no manual re-entry."),
            ("", "Shared cross-team views + a unified data model."),
            ("", "One-way direction; covers ReCred + Initial Cred."),
        ],
        "tdd": [
            ("", "Generalize RCAT eligibility to PDM push."),
            ("", "Cross-team worklist + shared record views."),
            ("", "Cred to PDM field mapping + de-duplication."),
        ],
        "risk": "Overlaps F3 & F4 — booked net-new to avoid double-counting shared foundations.",
        "reuse": "Builds directly on F3 worklists and the F4 versioned model. Sequence after both.",
    },
    {
        "n": 6, "name": "Inventory Management & Reporting",
        "size": "L–XL", "conf": "Low–Medium", "ai": "44–74", "base": "61–110",
        "scope": [
            ("", "OOTB reports + dashboards for leadership and operations."),
            ("", "Integrity / operational feed automation."),
            ("", "Work-inventory & backlog visibility for leadership."),
        ],
        "tdd": [
            ("", "Field-change extract engine for granular deltas."),
            ("", "Per-feed parity validation against source systems."),
            ("", "Throughput / backlog / aging dashboards."),
        ],
        "risk": "The integrity-feed count is unknown — a discovery inventory gates the upper end of the range. Reporting is near-greenfield today (5 reports and 1 dashboard exist), though 45 report types give a usable foundation.",
        "reuse": "Field-history source comes from F4; worklists / inventory from F3.",
    },
    {
        "n": 7, "name": "Mass Data Load Capabilities",
        "size": "XXL", "conf": "Medium (Foundational)", "ai": "123–172", "base": "187–263",
        "scope": [
            ("", "Build the reusable async mass-load engine."),
            ("", "Refactor 3 high-volume flows onto the engine."),
            ("", "7+ distinct mass operations (CSV / bulk + QC routing)."),
        ],
        "tdd": [
            ("", "PRM_AsyncJob engine: orchestrator, batch, dead-letter queue, progress LWC."),
            ("", "Per-operation: payload validator + batch + QC routing."),
            ("", "Metadata-driven sequencing, halt-on-failure, and retry."),
        ],
        "risk": "Engine is confirmed not built (the async job objects do not exist), though there is a head start: the service base and utility classes are deployed, the async constants are already defined, and 71 batch classes exist as precedent. The number of operations dominates effort — confirm the exact 7+ list.",
        "reuse": "The engine is consumed by F1, F5, and F8. Build this first.",
    },
    {
        "n": 8, "name": "Lexis Nexis Integration + Compliance Mandates",
        "size": "XL", "conf": "LN Med / Compliance Low", "ai": "82–134", "base": "117–185",
        "scope": [
            ("", "LexisNexis inbound: phone update, directory suppression."),
            ("", "Practitioner terminations + roster attestation."),
            ("", "Compliance mandates: a discovery spike + reserved envelope."),
        ],
        "tdd": [
            ("", "Reuse PRM_AsyncProcess staging to Platform Event to batch to outbound."),
            ("", "Termination cascade (Full / Non-Par / Last-Man-Standing)."),
            ("", "Compliance sized after the discovery spike."),
        ],
        "risk": "The termination cascade is a large hidden chunk; compliance scope is undefined until the spike. A LexisNexis feature toggle is already wired into 10 Integration Procedures in the address / PAR pipeline, but no LexisNexis credential exists — so the API call itself is still net-new.",
        "reuse": "Uses the F4 versioned model for terminations and the F7 async engine for feeds.",
    },
    {
        "n": 9, "name": "System Stabilization & Technical Debt Reduction",
        "size": "L–XL", "conf": "Medium (Continuous)", "ai": "170–320 (envelope)", "base": "230–400 (envelope) · known floor 94–171 / 59–108 AI",
        "scope": [
            ("", "Burn down ~40 documented defects / debt items / manual data scripts."),
            ("", "Reserve a ~15–20% annual capacity envelope."),
            ("", "Root-cause fixes for recurring failure classes."),
        ],
        "tdd": [
            ("", "Triage & register; prioritized burn-down."),
            ("", "Regression tests around every fix."),
            ("", "Exclude items owned by F3 / F4 / F7 to avoid double-counting."),
        ],
        "risk": "A continuous cost that competes directly with feature capacity — must be reserved, not assumed.",
        "reuse": "Runs across all four quarters alongside every other workstream.",
    },
    {
        "n": 10, "name": "Re-Cred PSV Add/Remove Location \u2192 Auto-Route to PDM",
        "size": "XL", "conf": "Medium", "ai": "95\u2013150", "base": "150\u2013230",
        "scope": [
            ("", "Re-enable add / remove of a practice location during the Re-Cred PSV process — today it is paused and the Re-Cred team emails PDM manually."),
            ("", "On a location change, automatically create and route a case to the PDM / Re-Cred PDA (RCAT) team — replacing the manual email."),
            ("", "Scope a location removal to the single affiliation being acted on, not every practitioner at the location."),
        ],
        "tdd": [
            ("", "Deploy the async practice-location processor so high-volume CAQH location sets no longer time out (shares the F7 engine)."),
            ("", "Fix the Re-Cred PDA Update P0 defects: location-removal mass-termination (Bug 1216121), QC Errors-Found table leak (Bug 1216120), and terminated-location 'Required Fields Missing'."),
            ("", "Route the location change to PDM via Case / Case Manager (RCAT pickup) and harden partial-write rollback so a mid-chain failure leaves no orphans."),
        ],
        "risk": "Paused in production for high-volume timeouts and P0 data-integrity defects; a safe resume is gated on the async processor + defect fixes (per the 2026-06-08 readiness audit). Confirm the fixes are the active org versions before lifting the email-only hold.",
        "reuse": "Async processor overlaps F7; effective-date / termination fixes overlap F4; QC case routing overlaps F3 — book largely net of those.",
    },
    {
        "n": 11, "name": "FHNatic — Provider Forms External Portal Exposure",
        "size": "XL", "conf": "Low\u2013Medium", "ai": "90\u2013140", "base": "90\u2013140",
        "scope": [
            ("", "Expose four existing internal provider forms on the external provider portal for self-service: PAR Form, Non-Par Registration, Provider Change Request, and Ancillary Cred Guided Flow."),
            ("", "Providers submit their own requests directly instead of internal teams keying them in."),
            ("", "Per-form external UI/UX, data validation, portal integration, and security."),
        ],
        "tdd": [
            ("", "Update and expose each existing internal guided flow externally — reuse, don't rebuild."),
            ("", "Make the ~17 custom components used by these four forms community-ready, then re-test each form in the external context."),
            ("", "External-user UI/UX adjustments, field validation, and community security / FLS per form."),
        ],
        "risk": "Re-sized upward from the original 32\u201352 story points. The provider portal already exists, which helps \u2014 but only 15 of 192 custom components are community-enabled today, and these four forms are the highest-churn assets in the org (one is on version 117). Community enablement and regression on those components were not in the original per-form figure.",
        "reuse": "Shares the external-portal foundation with F1 (PEAR self-service) and reuses the existing internal guided flows — book net of F1's portal work.",
    },
    {
        "n": 12, "name": "POMS Replacement — Multi-Request PDM Submission",
        "size": "XL", "conf": "Low\u2013Medium", "ai": "80\u2013120", "base": "80\u2013120",
        "scope": [
            ("", "Replace legacy POMS: let Network Coordinators submit multiple PDM update requests in a single action."),
            ("", "New UI for multi-request submission plus a processing workflow that creates / updates many records from one submission."),
            ("", "Reuse the existing PDM Manual Updates guided flow for individual record processing."),
        ],
        "tdd": [
            ("", "New multi-request intake UI + submission workflow."),
            ("", "Bulk data-handling framework to fan one submission out into many record updates (leverage the F7 async engine)."),
            ("", "Reuse the PDM Manual Updates guided flow per record."),
        ],
        "risk": "Original estimate 80\u2013120 story points. The PDM Manual Update family being reused is large (7 guided flows, ~99 steps), so the per-record reuse is real but the multi-request wrapper is the work. The bulk-handling framework overlaps F7 — net-new is lower if F7's async engine lands first.",
        "reuse": "Strong overlap with F7 (bulk framework) and the existing PDM Manual Updates guided flow. Sequence after F7; book net of the engine.",
    },
]

GLANCE = [
    ("1", "PDM Efficiency + PEAR Self-Service", "59–73", "84–107", "XL", "Med"),
    ("2", "Credentialing Enhancements", "211–281", "322–421", "XXL", "Mixed"),
    ("3", "Enhanced Case Management", "47–68", "68–100", "L–XL", "Med"),
    ("4", "Full Provider Data Versioning", "220–270", "475–490", "XXL", "Med / High-risk"),
    ("5", "Cred + PDM Integration", "34–52", "50–75", "L", "Med"),
    ("6", "Inventory Management & Reporting", "44–74", "61–110", "L–XL", "Low–Med"),
    ("7", "Mass Data Load Capabilities", "123–172", "187–263", "XXL", "Med"),
    ("8", "Lexis Nexis + Compliance", "82–134", "117–185", "XL", "LN Med / Comp Low"),
    ("9", "Stabilization & Tech Debt", "170–320", "230–400", "L–XL", "Med"),
    ("10", "Re-Cred PSV Add/Remove Location → PDM Routing", "95–150", "150–230", "XL", "Med"),
    ("11", "FHNatic — Provider Forms External Portal", "90–140", "90–140", "XL", "Low–Med"),
    ("12", "POMS Replacement — Multi-Request PDM", "80–120", "80–120", "XL", "Low–Med"),
]

OVERLAP = [
    ("Async / bulk engine (PRM_AsyncJob__c)", "F7", "F1 (PDM bulk edits), F5, F10 (PSV location processor), F12 (POMS bulk)"),
    ("External-submission QC routing (Case / CM / CDM + CMA)", "F7", "F3, F5, F8, F10  (note: PEAR is direct, no QC)"),
    ("External provider portal foundation", "F1", "F11 (FHNatic forms)"),
    ("PDM Manual Updates guided flow", "existing", "F12 (POMS per-record processing)"),
    ("Versioned / effective-dated write model", "F4", "F5 (no re-entry), F6 (history feeds), F8 (termination)"),
    ("Analyst worklists / routing", "F3", "F5 (shared views), F6 (leadership inventory)"),
    ("Field-history data source", "F4", "F6 (integrity feeds)"),
    ("Tile + session UI framework", "F2", "F7 mass-update grid cells"),
]

T_SHIRT = [
    ("S",   "~5–15 dev-days",     "Small, isolated change to one component."),
    ("M",   "~15–35 dev-days",    "Single component or flow, self-contained."),
    ("L",   "~35–75 dev-days",    "Multi-component feature with integration."),
    ("XL",  "~75–150 dev-days",   "Cross-cutting; multiple teams / systems touched."),
    ("XXL", "~150–300+ dev-days", "Multi-quarter program; may need parallel teams."),
]

MULTIPLIERS = [
    ("Apex / service layer", "~3x"),
    ("Unit / integration tests", "~4x"),
    ("Lightning Web Components", "~3x"),
    ("Triggers", "~2.5x"),
    ("OmniStudio (IP / DR / OS)", "~1.5x"),
    ("Integration / E2E", "~1.1x"),
    ("UAT / business validation", "~1x"),
]

OPEN_Q = [
    ("F2", "Name the exact step list for the '5 flows' — is it ~55 tiles or the ~108 steps the audit counts? Confirm CAQH document entitlement; all-5-flows in one year needs parallel teams."),
    ("F4", "Approve Tier 1 = the 14 highest-traffic objects (~80% of the write path); resolve the 7 pre-conditions + natural keys. Also confirm the history-tracking limit on Individual Application, which shows 61 tracked fields."),
    ("F5", "Confirm cred tracks (ReCred / Initial / PAR) + outcome-to-PDM matrix."),
    ("F6", "Run the integrity-feed discovery inventory (count unknown)."),
    ("F7", "Confirm the exact 7+ mass-operation list."),
    ("F8", "Define the compliance mandate(s) + deadline."),
    ("F9", "Confirm reserved % (15–20% proposed) and the double-count boundary."),
    ("F10", "Resume scope — all recred locations vs low-volume first; confirm the async processor + P0 defect fixes are deployed before lifting the email-only hold."),
    ("F11", "Which of the ~17 components used by the four forms are already community-safe, and how much of F1's portal foundation is reusable?"),
    ("F12", "Confirm the multi-request volume and whether POMS's bulk framework is fully covered by F7's async engine (to avoid rebuild)."),
    ("All", "Provide real sprint velocity — these sizes are structure-based, and the repo history is a one-month snapshot that offers no velocity signal."),
]


# ── build ────────────────────────────────────────────────────────────────
def main():
    doc = Document()

    # base style
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)

    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)

    # ── COVER ──
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    run(p, "INDEPENDENCE BLUE CROSS  ·  PROVIDER INFORMATION EXCHANGE (PIE)", size=10, bold=True, color=IBX_LIGHT)

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    run(p, "2027 Priorities", size=30, bold=True, color=IBX_BLUE)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    run(p, "ROM & Delivery Roadmap", size=20, bold=True, color=IBX_MED)
    add_bottom_border(doc.add_paragraph(), hex_color=BLUE_HEX)

    para(doc,
         "Twelve business priorities with T-shirt-sized delivery effort, scope, dependencies, risks, and a "
         "2027 roadmap.",
         size=11.5, color=IBX_MUTED, space_after=14)

    # cover stat table
    t = doc.add_table(rows=1, cols=4)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    style_table_borders(t, hex_color="FFFFFF", size=0)
    stats = [("12", "Business Priorities"), ("3", "XXL Programs (F2·F4·F7)"),
             ("4", "Quarter Roadmap"), ("5–7", "Senior Engineers, Full Year")]
    for i, (num, lab) in enumerate(stats):
        c = t.rows[0].cells[i]
        set_cell_bg(c, BLUE_HEX)
        set_cell_margins(c, top=140, bottom=140)
        pn = c.paragraphs[0]
        pn.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pn.paragraph_format.space_after = Pt(0)
        run(pn, num, size=19, bold=True, color=WHITE)
        pl = c.add_paragraph()
        pl.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run(pl, lab, size=8.5, color=RGBColor(0xCF, 0xDD, 0xF2))

    para(doc, "", space_after=6)
    p = doc.add_paragraph()
    run(p, "Confidential · For Internal Planning · July 2026", size=9, italic=True, color=IBX_MUTED)

    doc.add_page_break()

    # ── 1. SIZING KEY + AT A GLANCE ──
    heading(doc, "1.  Estimation Approach — T-Shirt Sizing", size=17, border=True)
    para(doc, "Each priority is estimated with a relative T-shirt size. The table below is the reference "
              "key that translates each size into an indicative developer-day range.",
         color=IBX_MUTED, space_after=8)

    kt = doc.add_table(rows=1, cols=3)
    style_table_borders(kt)
    k_headers = ["T-Shirt Size", "Estimated Dev-Days", "Typical Scope"]
    k_widths = [1.3, 1.8, 3.6]
    for i, (txt, w) in enumerate(zip(k_headers, k_widths)):
        c = kt.rows[0].cells[i]
        set_cell_bg(c, BLUE_HEX)
        set_cell_margins(c)
        c.width = Inches(w)
        run(c.paragraphs[0], txt, bold=True, color=WHITE, size=10)
    for idx, (sz, dd, scope) in enumerate(T_SHIRT):
        cells = kt.add_row().cells
        if idx % 2 == 1:
            for c in cells:
                set_cell_bg(c, GREY_HEX)
        for i, (val, w) in enumerate(zip((sz, dd, scope), k_widths)):
            set_cell_margins(cells[i])
            cells[i].width = Inches(w)
            if i == 0:
                run(cells[i].paragraphs[0], val, bold=True, color=IBX_BLUE, size=10)
            elif i == 1:
                run(cells[i].paragraphs[0], val, bold=True, color=IBX_GREEN, size=10)
            else:
                run(cells[i].paragraphs[0], val, size=10)
    para(doc, "Ranges are indicative planning bands; actual effort is refined per priority during build planning.",
         italic=True, color=IBX_MUTED, space_after=8, size=9.5)

    heading(doc, "The twelve priorities at a glance", size=13, color=IBX_MED)
    gt = doc.add_table(rows=1, cols=4)
    style_table_borders(gt)
    headers = ["#", "Priority", "Size", "Confidence"]
    widths = [0.4, 3.9, 0.9, 1.5]
    for i, (txt, w) in enumerate(zip(headers, widths)):
        c = gt.rows[0].cells[i]
        set_cell_bg(c, BLUE_HEX)
        set_cell_margins(c)
        c.width = Inches(w)
        run(c.paragraphs[0], txt, bold=True, color=WHITE, size=10)
    for idx, r in enumerate(GLANCE):
        # r = (#, name, estimate, baseline, size, confidence) -> show #, name, size, confidence
        row = (r[0], r[1], r[4], r[5])
        cells = gt.add_row().cells
        if idx % 2 == 1:
            for c in cells:
                set_cell_bg(c, GREY_HEX)
        for i, val in enumerate(row):
            set_cell_margins(cells[i])
            cells[i].width = Inches(widths[i])
            pcell = cells[i].paragraphs[0]
            if i == 0:
                run(pcell, val, bold=True, color=IBX_BLUE, size=10)
            elif i == 1:
                run(pcell, val, bold=True, size=10)
            elif i == 2:
                run(pcell, val, bold=True, color=IBX_MED, size=10)
            else:
                run(pcell, val, size=10)

    para(doc, "", space_after=6)
    heading(doc, "Portfolio size mix", size=13, color=IBX_MED)
    bullet(doc, "XXL (3):", "F2 Credentialing, F4 Data Versioning, F7 Mass Data Loads — multi-quarter programs. F2 and F4 each exceed twice the floor of the XXL band and should be funded in phases, not as single items.", label_color=IBX_RED)
    bullet(doc, "XL (5):", "F1 PDM + PEAR, F8 Lexis Nexis + Compliance, F10 Re-Cred PSV Location → PDM, F11 FHNatic Provider Forms, F12 POMS Replacement.", label_color=IBX_ORANGE)
    bullet(doc, "L–XL (3):", "F3 Case Management, F6 Inventory & Reporting, F9 Stabilization.", label_color=IBX_ORANGE)
    bullet(doc, "L (1):", "F5 Cred + PDM Integration.", label_color=IBX_GREEN)

    para(doc, "Priorities 11–12 (FHNatic, POMS) are carried in from the Oct 2025 'FHNatic / POMS / Mass Grid' "
              "estimate (originally in story points; shown here mapped to T-shirt sizes). That document's Mass "
              "Grid initiative is already represented by Priority 7 (Mass Data Load Capabilities).",
         italic=True, color=IBX_MUTED, space_after=6, size=9.5)

    doc.add_page_break()

    # ── 2. PER-FEATURE ──
    heading(doc, "2.  Priority Detail", size=17, border=True)
    for f in FEATURES:
        heading(doc, f"Priority {f['n']} — {f['name']}", size=14, color=IBX_BLUE, space_before=12, space_after=4)

        # effort strip
        et = doc.add_table(rows=1, cols=2)
        style_table_borders(et)
        effort = [("T-Shirt Size", f["size"], IBX_MED), ("Confidence", f["conf"], IBX_ORANGE)]
        for i, (lab, val, col) in enumerate(effort):
            c = et.rows[0].cells[i]
            set_cell_bg(c, LIGHT_HEX)
            set_cell_margins(c)
            pl = c.paragraphs[0]
            pl.paragraph_format.space_after = Pt(0)
            run(pl, lab.upper(), size=8, bold=True, color=IBX_MUTED)
            pv = c.add_paragraph()
            run(pv, val, size=11, bold=True, color=col)

        para(doc, "", space_after=2)
        p = doc.add_paragraph(); run(p, "What we're delivering", bold=True, color=IBX_GREEN, size=11)
        for lbl, txt in f["scope"]:
            bullet(doc, lbl, txt, label_color=IBX_GREEN)
        p = doc.add_paragraph(); run(p, "How we'll build it (high-level TDD)", bold=True, color=IBX_MED, size=11)
        for lbl, txt in f["tdd"]:
            bullet(doc, lbl, txt)

        pr = doc.add_paragraph(); pr.paragraph_format.space_after = Pt(2)
        run(pr, "Top risk:  ", bold=True, color=IBX_RED, size=10.5)
        run(pr, f["risk"], size=10.5)
        pu = doc.add_paragraph(); pu.paragraph_format.space_after = Pt(10)
        run(pu, "Reuse / dependency:  ", bold=True, color=IBX_GREEN, size=10.5)
        run(pu, f["reuse"], size=10.5)

    doc.add_page_break()

    # ── 3. OVERLAP ──
    heading(doc, "3.  Shared Foundations — Read Before Summing", size=17, border=True)
    para(doc, "Several priorities depend on the same building blocks. Each foundation is booked once with its "
              "primary owner; consumers reuse it. Sequencing foundation-first turns overlap into savings.",
         color=IBX_MUTED, space_after=8)

    ot = doc.add_table(rows=1, cols=3)
    style_table_borders(ot)
    for i, txt in enumerate(("Shared foundation", "Primary owner", "Also consumed by")):
        c = ot.rows[0].cells[i]
        set_cell_bg(c, BLUE_HEX)
        set_cell_margins(c)
        run(c.paragraphs[0], txt, bold=True, color=WHITE, size=10)
    for idx, (found, owner, cons) in enumerate(OVERLAP):
        cells = ot.add_row().cells
        if idx % 2 == 1:
            for c in cells:
                set_cell_bg(c, GREY_HEX)
        for c in cells:
            set_cell_margins(c)
        run(cells[0].paragraphs[0], found, size=10, bold=True)
        run(cells[1].paragraphs[0], owner, size=10, bold=True, color=IBX_TEAL)
        run(cells[2].paragraphs[0], cons, size=10)

    para(doc, "", space_after=4)
    bullet(doc, "Build foundations first:", "F7 async engine and F4 versioning are the two spines.")
    bullet(doc, "Net-new already deducted:", "F5 is booked net-of-overlap; F9 excludes items owned by F3/F4/F7.")
    bullet(doc, "Sequencing saves effort:", "F7→F1, F4→(F5/F6/F8), F3→(F5/F6) reuse work already paid for.")

    doc.add_page_break()

    # ── 4. TIMELINE ──
    heading(doc, "4.  2027 Delivery Timeline & Sequencing", size=17, border=True)
    tl = doc.add_table(rows=1, cols=5)
    style_table_borders(tl)
    tl_headers = ["Workstream", "Q1 · Foundations", "Q2 · Build", "Q3 · Scale", "Q4 · Harden & Cut Over"]
    for i, txt in enumerate(tl_headers):
        c = tl.rows[0].cells[i]
        set_cell_bg(c, BLUE_HEX)
        set_cell_margins(c)
        run(c.paragraphs[0], txt, bold=True, color=WHITE, size=9.5)
    tl_rows = [
        ("Async & Mass Load", "F7 engine build", "F7 first ops + F1 PEAR", "F7 remaining mass ops", "—"),
        ("Versioning", "F4 architecture", "F4 Tier-1 objects", "F4 Tier-2 / 3 objects", "F4 parity + cutover"),
        ("Credentialing", "—", "F2 tile framework (parallel team)", "F2 CAQH docs + flow migrations", "F2 Agentic pilots go-live"),
        ("Case / Integ / Report", "F3 routing + defect fix", "F10 Re-Cred PSV→PDM (defects + async)", "F5 integration + F6 reports", "F6 integrity feeds + dashboards"),
        ("Feeds & Compliance", "—", "F8 LexisNexis on engine", "F8 terminations + spike", "F8 compliance build"),
        ("External Portal / POMS", "—", "F11 FHNatic forms (reuse F1 portal)", "F12 POMS multi-request (on F7 engine)", "—"),
        ("Stabilization (F9)", "Continuous ~15–20% reserved capacity across all four quarters", "", "", ""),
    ]
    for ridx, r in enumerate(tl_rows):
        cells = tl.add_row().cells
        if r[0].startswith("Stabilization"):
            set_cell_bg(cells[0], "FFF6D0"); set_cell_margins(cells[0])
            run(cells[0].paragraphs[0], r[0], size=9.5, bold=True, color=IBX_ORANGE)
            merged = cells[1].merge(cells[4])
            set_cell_bg(merged, "FFF6D0"); set_cell_margins(merged)
            run(merged.paragraphs[0], r[1], size=9.5, bold=True, color=IBX_ORANGE)
            continue
        for i, val in enumerate(r):
            set_cell_margins(cells[i])
            if i == 0:
                set_cell_bg(cells[i], LIGHT_HEX)
                run(cells[i].paragraphs[0], val, size=9.5, bold=True, color=IBX_BLUE)
            else:
                if val and val != "—":
                    set_cell_bg(cells[i], GREY_HEX)
                run(cells[i].paragraphs[0], val, size=9.5)

    para(doc, "", space_after=6)
    bullet(doc, "Q1 — Foundations:", "Stand up F7 async engine, start F4 architecture and F3 routing.")
    bullet(doc, "Q2–Q3 — Build & Scale:", "F1 + F8 on the engine; F4 object tiers; F2 tiles (parallel team); F5/F6 as F3/F4 land.")
    bullet(doc, "Q4 — Harden & Cut Over:", "Versioning parity + cutover, Agentic pilots (post F2), and compliance build (post spike).")

    doc.add_page_break()

    # ── 5. TOTALS ──
    heading(doc, "5.  Portfolio Sizing & Resource Mix", size=17, border=True)
    heading(doc, "Portfolio size profile", size=13, color=IBX_MED)
    bullet(doc, "Size mix:", "3 XXL + 5 XL + 3 L–XL + 1 L across the twelve priorities.")
    bullet(doc, "Heavy hitters:", "the three XXL programs (F2, F4, F7) dominate the portfolio and drive the timeline.")
    heading(doc, "Team & resource mix", size=13, color=IBX_MED)
    bullet(doc, "Staffing:", "~5–7 senior engineers sustained across the full year.")
    bullet(doc, "Roles:", "Apex / Platform, OmniStudio, LWC, QA, Data / Integration, PM / BA.")
    bullet(doc, "Parallelism:", "F2, F4, and F7 are three concurrent multi-quarter programs.")

    p = doc.add_paragraph()
    shade_paragraph(p, "FFF6D0")
    p.paragraph_format.space_before = Pt(8)
    run(p, "Read the sizing as indicative.  ", bold=True, color=IBX_ORANGE, size=10.5)
    run(p, "F9 is a reserved capacity envelope and F5 is booked net-new; several priorities share foundations. "
            "Sequence foundations first — don't sum the sizes naively. See the sizing key in Section 1 for "
            "the T-shirt to dev-day translation.", size=10.5)

    heading(doc, "Capacity reality check", size=13, color=IBX_RED)
    para(doc, "Translating the twelve T-shirt sizes through the Section 1 key gives a portfolio of roughly "
              "2,130–3,020 developer-days, or about 9–13 developer-years. A team of 5–7 senior engineers supplies "
              "roughly 1,150–1,610 developer-days in a year. The portfolio as scoped is therefore about twice what "
              "the stated team can deliver in 2027.")
    bullet(doc, "Option A —", "Increase staffing to roughly 9–13 engineers.", label_color=IBX_RED)
    bullet(doc, "Option B —", "Phase the portfolio: deliver F7 (engine + first operations), F4 Tier 1, F3, F1, F10 and F2 Phase 1, with the F9 envelope. That slice fits 5–7 engineers.", label_color=IBX_GREEN)
    bullet(doc, "Option C —", "Cut scope outright — defer F5, F6, F8, F11 and F12 to 2028.", label_color=IBX_ORANGE)
    para(doc, "The single highest-leverage scope decision is F4: limiting versioning to the 14 highest-traffic "
              "objects captures roughly 80% of the write path for about half the cost.", italic=True, color=IBX_MUTED, size=9.5)

    doc.add_page_break()

    # ── 6. RISKS & OPEN QUESTIONS ──
    heading(doc, "6.  Risks & Open Questions", size=17, border=True)
    heading(doc, "Top program risks", size=13, color=IBX_RED)
    bullet(doc, "Portfolio exceeds capacity:", "the twelve priorities total roughly twice what 5–7 engineers can deliver in 2027. Phasing or additional staffing is required — see the capacity reality check in Section 5.", label_color=IBX_RED)
    bullet(doc, "Versioning blast radius (F4):", "478 write-path Load DataMappers and 236 DML-performing Apex classes across 42 objects, plus 7 open pre-conditions.", label_color=IBX_RED)
    bullet(doc, "Credentialing scope boundary (F2):", "the credentialing family is 45 guided flows / 304 steps; the core 5 flows alone are ~108 steps against the ~55 tiles originally assumed.", label_color=IBX_RED)
    bullet(doc, "Community component gap (F1 / F11):", "only 15 of 192 custom components are community-enabled, so any provider-facing screen carries an enablement and re-test cost.", label_color=IBX_RED)
    bullet(doc, "CAQH document API (F2):", "connectivity exists, but document entitlement is unverified.", label_color=IBX_RED)
    bullet(doc, "Compliance scope (F8):", "undefined until the discovery spike.", label_color=IBX_RED)
    bullet(doc, "Re-Cred PSV route paused (F10):", "resume is gated on the async location processor + P0 data-integrity defects (Bug 1216121 / 1216120, terminated-location) per the 2026-06-08 audit.", label_color=IBX_RED)
    bullet(doc, "Fixed-cost work:", "OmniStudio publish, UAT, shadow parity, and integration testing do not compress.", label_color=IBX_RED)

    heading(doc, "Open questions carried forward", size=13, color=IBX_MED)
    qt = doc.add_table(rows=1, cols=2)
    style_table_borders(qt)
    for i, txt in enumerate(("Feature", "Open question")):
        c = qt.rows[0].cells[i]
        set_cell_bg(c, BLUE_HEX)
        set_cell_margins(c)
        run(c.paragraphs[0], txt, bold=True, color=WHITE, size=10)
    for idx, (feat, q) in enumerate(OPEN_Q):
        cells = qt.add_row().cells
        if idx % 2 == 1:
            for c in cells:
                set_cell_bg(c, GREY_HEX)
        set_cell_margins(cells[0]); set_cell_margins(cells[1])
        cells[0].width = Inches(0.9)
        run(cells[0].paragraphs[0], feat, bold=True, color=IBX_BLUE, size=10)
        run(cells[1].paragraphs[0], q, size=10)

    # ── 7. NEXT STEPS ──
    heading(doc, "7.  Next Steps & Decisions", size=17, border=True, space_before=16)
    heading(doc, "Decisions to make now", size=13, color=IBX_GREEN)
    bullet(doc, "1.", "Confirm the per-feature scope.", label_color=IBX_GREEN)
    bullet(doc, "2.", "Decide: fund F2 / F4 / F7 as parallel programs, or phase them across the year.", label_color=IBX_GREEN)
    bullet(doc, "3.", "Approve the reserved stabilization capacity (~15–20%).", label_color=IBX_GREEN)
    heading(doc, "Discovery spikes to schedule", size=13, color=IBX_ORANGE)
    bullet(doc, "", "CAQH document API entitlement & access.", label_color=IBX_ORANGE)
    bullet(doc, "", "Integrity-feed inventory (count & parity rules).", label_color=IBX_ORANGE)
    bullet(doc, "", "Compliance mandate(s) definition & deadline.", label_color=IBX_ORANGE)
    bullet(doc, "", "Mass-operation catalog — confirm the exact 7+ list.", label_color=IBX_ORANGE)

    para(doc, "", space_after=6)
    para(doc, "Each priority has a standalone TDD + estimation doc in requirements/2027_ROM_TDD/.",
         italic=True, color=IBX_MUTED)

    out = "/Users/pkothapalli/Documents/IBXQA/IBXQA/requirements/Enhancements/IBX_2027_Priorities_ROM.docx"
    doc.save(out)
    print("Saved:", out)


if __name__ == "__main__":
    main()
