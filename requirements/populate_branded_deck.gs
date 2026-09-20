/**
 * IBX SVP Briefing — Credentialing & PDM Platform Overview
 *
 * Populates the IBX deck by CLONING slides from the 2026 Salesforce Corporate
 * Template (preserves logos, fonts, master slides, footer/page-number elements)
 * and overwriting only the text in the title + body placeholders.
 *
 * Run order (in Apps Script editor at script.google.com):
 *   1. listTemplateSlides()  — confirm SOURCE_BY_KIND mapping is still correct
 *                               for the current template revision (View → Logs).
 *   2. cloneAndPopulate()    — wipes the target deck, clones the chosen template
 *                               slides, and writes our SVP content + speaker notes.
 *
 * Audience: SVP. Tone: executive, quantitative, low jargon.
 * Last updated: 2026-05-21
 */

const TEMPLATE_ID = '1WR4O_urDIWBB4qbr073CNNEI_kHBG_GN3R9B3ufmWCI'; // 2026 Salesforce Corporate Template
const DECK_ID     = '1ZSLvtWWHH67stqLfjvsEm0VYbAt-MqjqGZ50NWZCNKg'; // IBX Credentialing & PDM V1

// ---------------------------------------------------------------------------
// STEP 1 — Run this first to verify the template's slide layout indices.
// ---------------------------------------------------------------------------
function listTemplateSlides() {
  const tpl = SlidesApp.openById(TEMPLATE_ID);
  const slides = tpl.getSlides();
  Logger.log('Template "%s" has %d slides', tpl.getName(), slides.length);

  slides.forEach((slide, idx) => {
    const labels = [];
    const shapes = slide.getShapes();
    for (const shape of shapes) {
      try {
        const tr = shape.getText();
        const text = tr ? tr.asString() : '';
        if (text && text.trim()) {
          labels.push(text.replace(/\s+/g, ' ').trim().slice(0, 80));
          if (labels.length >= 2) break;
        }
      } catch (e) {}
    }
    const layoutName = (() => {
      try { return slide.getLayout().getLayoutName(); }
      catch (e) { return '?'; }
    })();
    Logger.log('[%d] layout="%s"  text="%s"', idx + 1, layoutName,
               labels.join('  ||  ') || '(no text)');
  });
}

// ---------------------------------------------------------------------------
// Template source-slide map (1-based, matches Slides UI numbering).
// Update these if listTemplateSlides() shows the template was reorganized.
// ---------------------------------------------------------------------------
const SOURCE_BY_KIND = {
  cover:          18,   // "Title of presentation / Subtitle" — clean SF cover
  titleAndBody:   21,   // "Agenda" — title + bulleted body, our standard content slide
  sectionHeader:  55,   // "Segue / Subtitle" — section divider
  thankYou:       50    // "Bold statement" — strong close
};

// ---------------------------------------------------------------------------
// SVP DECK — 13 slides
// ---------------------------------------------------------------------------
const SLIDES = [

  // 1
  { kind: 'cover',
    title: 'Provider Network Management',
    subtitle: 'Credentialing & Provider Data Management — Platform Overview\nIBX × Salesforce  ·  SVP Briefing  ·  May 2026',
    notes: 'Set context. 20-min briefing on the platform that runs IBX provider credentialing and ongoing provider data management. We will cover what the platform does today, the scale it operates at, where the friction is, and where we are investing next.' },

  // 2
  { kind: 'titleAndBody', title: 'Why this matters to IBX', body: [
      'Speed to network — faster credentialing means providers billing earlier and lower abrasion with practices',
      'Data accuracy — PDM directly drives directory accuracy, claims routing, and CMS / NCQA compliance posture',
      'Operational cost — every stuck application or silent failure burns case-manager hours and erodes provider satisfaction',
      'Audit readiness — credentialing decisions must be traceable, layered, and defensible to internal audit and external regulators'],
    notes: 'Open with the business "why" before any architecture. Ground the SVP in revenue (faster billing), risk (directory and CMS compliance), and cost (case-manager burn rate). Tie to recent ops feedback if the SVP is closer to ops than tech.' },

  // 3
  { kind: 'titleAndBody', title: 'Platform at a glance', body: [
      'One Salesforce-native platform — Health Cloud, OmniStudio (OmniScripts, IPs, DataRaptors, FlexCards), Lightning Web Components, Apex, Salesforce Flow',
      '100 guided flows (OmniScripts) covering the full provider lifecycle — onboarding, credentialing, ongoing PDM, termination, reinstatement, ancillary',
      '533 Apex classes  ·  402 Integration Procedures  ·  1,327 DataRaptors  ·  165 LWCs  ·  46 batch jobs  ·  21 platform flows',
      'Approximately 2,588 production artifacts — mature, in steady state, and actively extended every quarter',
      'No off-platform runtime — everything runs natively on Salesforce; integrations are managed callouts'],
    notes: 'The number to land is "2,500+ production artifacts." The SVP needs to grasp that the surface area is large and that changes here are non-trivial. Skip the OmniStudio primer — she does not need it.' },

  // 4
  { kind: 'titleAndBody', title: 'End-to-end provider lifecycle', body: [
      'Onboarding (Credentialing) — PAR Application → App Review → PSV → PDA → QC Review → HACAC Committee (non-routine) → Activation',
      'Ongoing (PDM) — Provider Change Form → PDM Manual Update flows → Re-Credentialing → Termination → Reinstatement',
      'Initial credentialing is a once-per-provider event; PDM is the daily-ops layer that keeps directory and claims data correct',
      'A provider record can re-enter the cycle: Reinstatement loops back into Application Review',
      'Every stage is backed by a guided flow and an audit-ready case record'],
    notes: 'This is the only slide where we show the whole lifecycle. Walk it left to right verbally. Initial cred is a once-per-provider event. PDM is the ongoing ops layer that runs the rest of the time. Re-cred, termination, and reinstatement all live in the ongoing ring.' },

  // 5
  { kind: 'titleAndBody', title: 'Credentialing — Initial Cred', body: [
      'Stage 1 — PAR Form submission (PRM_PractitionerParticipationForm) — single intake, drives downstream record creation',
      'Stage 2 — Application Review (PRM_InitialCredentialAppReview) — case manager triages, requests info, or denies',
      'Stage 3 — Primary Source Verification — independent verification against NPDB, state license boards, education sources',
      'Stage 4 — PDA (Professional Development Activities) — captures soft credential data',
      'Stage 5 — QC checkpoint (PRM_InitialCredPDAQC) — every cred decision passes through QC',
      'Stage 6 — HACAC Committee — non-routine cases only (PRM_NonRoutineCommitteeReview, PRM_ReviewHACAC)',
      'Stage 7 — Activation — cascading record creation, BCBSA sync, network and taxonomy records'],
    notes: 'Narrate the journey, do not read the boxes. "An applicant submits a PAR form, case manager picks it up, PSV verifies the license / NPDB / education, PDA captures soft data, QC catches issues, HACAC handles non-routine, and we activate." Mention CAQH and NPDB are the integration backbone — ties to slide 10.' },

  // 6
  { kind: 'titleAndBody', title: 'Credentialing — Re-Cred & Off-Cycle', body: [
      'Re-Credentialing (cyclical, every 2–3 years) — PRM_ReCredUpdate, PRM_ReCredQCUpdate, PRM_RecredQC',
      'Driven by 4 scheduled batches — due-date check, CAQH access check, notification email, letter generation',
      'CAQH re-validation is a hard gate — record cannot advance without a valid CAQH attestation',
      'Failure path recently hardened — re-cred letter fallback and silent-failure monitoring shipped',
      'Off-Cycle Credentialing (event-driven) — abbreviated PSV and accelerated QC for exception circumstances',
      'Re-cred drives the bulk of cred volume; off-cycle is lower volume but high-importance'],
    notes: 'The SVP needs to know there are two cred motions: a calendar-driven recred (the engine that keeps the network compliant) and an event-driven off-cycle motion (lower-volume but high-importance "exception" lane). Recred is by far the bigger volume driver.' },

  // 7
  { kind: 'titleAndBody', title: 'PSV, QC, and HACAC Committee', body: [
      'Three layers of review keep credential decisions defensible to internal audit, NCQA, and CMS',
      'Primary Source Verification — 4 OmniScripts including a dedicated NPDB sub-flow (PRM_PSVSubOsWSNPDB)',
      'Quality Control — 10 QC OmniScripts span manual updates, off-cycle, non-routine, HACAC, and delegated practitioners',
      'HACAC Committee — non-routine cases land here; output flows back into cred records and adverse action logs',
      'Every decision has a primary verification, a QC checkpoint, and a committee path for exceptions — full audit trail by design'],
    notes: 'This is the audit / compliance story. We have layered review, automated documentation, and an audit trail. Every cred decision has a primary verification, a QC checkpoint, and a committee path for exceptions. Useful slide if the SVP also covers risk / compliance.' },

  // 8
  { kind: 'sectionHeader',
    title: 'Provider Data Management',
    subtitle: 'How we keep the data correct after the cred decision',
    notes: 'Section divider. Pivot point: cred is a once-per-provider event; everything ahead of this slide is the ongoing data accuracy engine that runs every day.' },

  // 9
  { kind: 'titleAndBody', title: 'PDM — the ongoing data accuracy engine', body: [
      'PDM = how we keep practitioner, practice-location, group, and ancillary data accurate after the initial cred decision',
      'PRM_PDMManualChanges — demographic and association entry point',
      'PRM_PDMManualUpdatePractitioner — practitioner-level updates (taxonomy, NPI, demographics)',
      'PRM_PDMManualUpdate — practice-location updates (billing/mailing address, networks, capitation)',
      'PRM_PDMManualUpdateVendor — vendor / ancillary updates',
      'PRM_PDMManualUpdateHCFAssociations — healthcare facility ↔ network association updates',
      'Backed by 5-step QC review chain, cross-reference validation, Precisely address validation, future-dated activation'],
    notes: 'PDM is not a single flow — it is five guided flows plus a cross-reference and validation backbone. Most of what the network ops team does day-to-day lives here, not in credentialing. PDM volume dwarfs cred volume.' },

  // 10
  { kind: 'titleAndBody', title: 'Where the platform hurts today', body: [
      'High-volume submissions hit governor limits — practitioners with 3+ practice locations, 3+ taxonomies, 15+ networks generate 54+ records and exceed Salesforce 150-DML / 60s-CPU limits',
      'Operational impact: 5-minute UI freezes, silent partial saves, 15–20 support tickets per week, 2–3 hours remediation per ticket',
      'Capitated Bundle search caps at 500 of 1,582 active bundles — and the validation rule asks the wrong question (CAP program, not bundle membership). Blocks legitimate billing-address updates',
      'Edit-in-flow not supported — PSV / Cred reviewers see a wrong field, exit the flow, edit the record, restart. Tied to a 4 MB Save-for-Later payload limit',
      'These are the three loudest complaints — quantified, root-caused, and actively being unwound (next slides)'],
    notes: 'These are the three highest-frequency operational complaints. Deliberately quantified. Not airing dirty laundry — showing we know what hurts and we have plans for each.' },

  // 11
  { kind: 'titleAndBody', title: 'External integrations — we are a hub, not an island', body: [
      'CAQH — provider profile and attestation pre-fill, recred validation gate',
      'NPDB — adverse-action verification, runs as a sub-flow inside PSV',
      'Precisely API — address standardization and validation across every flow',
      'BCBSA — inter-Blue practitioner / role sync',
      'UPHS Roster + UPenn Roster — provider roster reconciliation (batch)',
      'NCPDP — pharmacy provider data',
      'RCAT — Roster Compliance & Attestation Tool, internal compliance feed',
      'Credentialing is a data-orchestration problem, not a data-entry problem — every cred decision touches at least 2 external systems'],
    notes: 'Credentialing is a data-orchestration problem, not a data-entry problem. Every cred decision touches at least 2 external systems; recred touches 3+. If any of these go down, downstream cred velocity drops. This is why we invest in batch resilience and async patterns.' },

  // 12
  { kind: 'titleAndBody', title: 'Recent wins & what is next', body: [
      'Shipped — Practitioner Creation async refactor (TX1/TX2/TX3 Queueable + Platform Event logging) — eliminates governor-limit failures for delegated practitioners',
      'Shipped — Failed Record Staging + retry quick action; re-cred letter fallback and silent-failure monitoring',
      'Shipped — Reusable Address Group Manager (Phase 5) — 4 reusable Apex services + LWC framework, drops cost of every subsequent address feature',
      'Next 90 days — Application Review LWC tile redesign (solves the 4 MB Save-for-Later cap), Re-credentialing flow polish, delegated-network batch re-architecture',
      'Strategic bet — Provider Data Versioning across 30 core objects: effective-dated history, audit support, back-dated correction. ~5–7 months calendar with senior devs + AI-assisted development',
      'Mass Updates and Mass Address Update — 65 SP and 28 SP respectively; replaces ~30–60 hours/week of manual roster work'],
    notes: 'Pick 3 to land verbally based on what is top-of-mind for the SVP. The async refactor is the highest-leverage one — it is the framework everything else builds on. Provider Data Versioning is the only multi-quarter strategic bet on this slide; flag it for sponsorship in the asks slide.' },

  // 13
  { kind: 'thankYou',
    title: 'Health metrics & asks',
    subtitle: 'KPIs we track  ·  Cred turnaround  ·  Re-cred completion within window  ·  PDM submission failure rate  ·  Performance-related ticket volume (15–20/wk → <5/wk target)\n\nWhat we need from you  ·  Sponsorship for Provider Data Versioning (multi-quarter)  ·  Provider Contracting decision on the PDM Bundle validation  ·  UAT bandwidth for the Practitioner Creation async cutover',
    notes: 'Two-column close. Left: how we know we are winning. Right: exactly what we need from you. Each ask is concrete and small enough to act on inside a single SVP staff meeting. Do not over-rehearse the closing line; let the asks land.' }
];

// ---------------------------------------------------------------------------
// STEP 2 — Clone source template slides into the deck and overwrite text.
// ---------------------------------------------------------------------------
function cloneAndPopulate() {
  const tpl  = SlidesApp.openById(TEMPLATE_ID);
  const deck = SlidesApp.openById(DECK_ID);

  // 1. Wipe deck, keep masters/layouts.
  const existing = deck.getSlides();
  const tmp = deck.appendSlide(SlidesApp.PredefinedLayout.BLANK);
  for (const s of existing) s.remove();

  // 2. Clone & populate.
  const tplSlides = tpl.getSlides();
  for (const spec of SLIDES) {
    let srcIdx = SOURCE_BY_KIND[spec.kind];
    if (srcIdx == null && spec.kind === 'thankYou') srcIdx = SOURCE_BY_KIND.sectionHeader;
    if (srcIdx == null) {
      throw new Error('No SOURCE_BY_KIND mapping for kind "' + spec.kind + '"');
    }
    const sourceSlide = tplSlides[srcIdx - 1];
    if (!sourceSlide) {
      throw new Error('Template slide #' + srcIdx + ' does not exist');
    }
    const cloned = deck.appendSlide(sourceSlide);
    overwriteText(cloned, spec);
    if (spec.notes) writeSpeakerNotes(cloned, spec.notes);
  }

  tmp.remove();
  Logger.log('Cloned %d slides from template "%s" into deck "%s"',
             SLIDES.length, tpl.getName(), deck.getName());
  Logger.log('Open the deck: https://docs.google.com/presentation/d/%s/edit', DECK_ID);
}

/**
 * Replace text in a cloned slide.
 *
 * Title  = shape with the largest font size (tiebreak: largest area).
 * Body   = largest remaining shape that is not a tiny decorative element
 *          (page number, "01" label, etc.). Empty placeholders are preferred
 *          over already-populated shapes — those are the real body slots
 *          inherited from the layout.
 *
 * Decorative shapes (sparkles, cloud icons, footer, page numbers) are left
 * untouched so the brand treatment survives.
 */
function overwriteText(slide, spec) {
  const shapes = slide.getShapes();
  const slideHeight = SlidesApp.openById(DECK_ID).getPageHeight();

  const cands = [];
  for (const shape of shapes) {
    let tr;
    try { tr = shape.getText(); } catch (e) { continue; }
    if (!tr) continue;

    const txt = tr.asString() || '';
    let topSize = 0;
    try {
      const runs = tr.getRuns();
      if (runs && runs.length) {
        const sz = runs[0].getTextStyle().getFontSize();
        if (sz) topSize = sz;
      }
    } catch (e) {}

    let top = 0, height = 0, width = 0;
    try { top = shape.getTop(); } catch (e) {}
    try { height = shape.getHeight(); } catch (e) {}
    try { width = shape.getWidth(); } catch (e) {}

    cands.push({
      shape: shape, tr: tr, text: txt,
      hasText: !!txt.trim(),
      size: topSize, area: width * height,
      width: width, height: height, top: top
    });
  }

  if (!cands.length) return;

  // TITLE — largest font, tiebreak by area.
  const byTitle = cands.slice().sort((a, b) =>
    (b.size - a.size) || (b.area - a.area));
  const titleCand = byTitle[0];

  // BODY — largest remaining shape, ignoring tiny decorative elements.
  const remaining = cands.filter(c => c.shape !== titleCand.shape);
  const ptHeight = slideHeight;
  const minHeight = ptHeight * 0.05;
  const minWidth = 100;
  let bodyPool = remaining.filter(c =>
    c.height >= minHeight && c.width >= minWidth);
  if (!bodyPool.length) bodyPool = remaining;

  // Empty placeholders first (they are the real body slots), then by area desc.
  bodyPool.sort((a, b) => {
    if (a.hasText !== b.hasText) return a.hasText ? 1 : -1;
    return b.area - a.area;
  });
  const bodyCand = bodyPool[0];

  // Write TITLE.
  if (spec.title && titleCand) {
    try { titleCand.tr.setText(spec.title); } catch (e) {}
  }

  // Write SUBTITLE or BODY bullets.
  if (bodyCand) {
    if (spec.subtitle) {
      try { bodyCand.tr.setText(spec.subtitle); } catch (e) {}
    } else if (spec.body && spec.body.length) {
      try {
        bodyCand.tr.setText(spec.body.join('\n'));
        try {
          bodyCand.tr.getListStyle()
            .applyListPreset(SlidesApp.ListPreset.DISC_CIRCLE_SQUARE);
        } catch (e2) {}
      } catch (e) {}
    }
  }

  // Decorative shapes are left untouched intentionally.
}

/**
 * Drop speaker notes into the slide's notes page.
 */
function writeSpeakerNotes(slide, text) {
  try {
    const notesPage = slide.getNotesPage();
    const notesShape = notesPage.getSpeakerNotesShape();
    if (notesShape) {
      notesShape.getText().setText(text);
    }
  } catch (e) {
    Logger.log('Could not write speaker notes: %s', e);
  }
}
