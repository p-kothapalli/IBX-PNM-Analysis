# Mass Address Update — Figma-Ready Component Layout Spec
### Salesforce UX handoff · SLDS spacing tokens · 4px grid · Compact + Comfortable density · Responsive annotations

> **Purpose.** A build-ready specification for reconstructing the *Mass Update Billing / Mailing Address* tool in Figma as an SLDS-conformant component library + screen set. Pairs with:
> - Visual reference (interactive): `../../.agents/artifacts/MassUpdate_BillingMailingAddress_Mockup.html`
> - Brand color/type tokens: `Mockup_Brand_Style_Guide.md` + `assets/brand-tokens.css`
> - Foundations sheet (import to Figma): `assets/MassAddressUpdate_Figma_Foundations.svg`
> - Backing architecture: `../Enhancements/PNM_MassAddressUpdate_FullStack_Architecture.md`
>
> **How to use in Figma.** Rebuild the **Foundations** page first (tokens as Variables), then the **Components** page (each as a Component with Variants for density), then assemble **Screens** from instances. Every measurement below is an SLDS spacing token; never type a raw px that isn't on the 4px grid.

---

## 1. Foundations

### 1.1 The grid
- **Base unit: 4px.** Every dimension is a multiple of 4 (the single exception is the `2px` hairline token `spacing-3x-small`, used only for inset rules/focus offsets).
- **Layout grid (Figma › Layout Grid):** 12 columns, **gutter 16px** (`spacing-medium`), **margin 24px** (`spacing-large`) at desktop. Column count collapses by breakpoint (§6).
- **Baseline:** 4px baseline grid for vertical rhythm. Text blocks snap line-box to 4px.

### 1.2 SLDS spacing tokens (the only spacing values allowed)

| Token (SLDS / SDS) | rem | **px** | On 4-grid | Typical use |
|---|---|---|---|---|
| `spacing-none` | 0 | 0 | ✓ | reset |
| `spacing-3x-small` | 0.125 | **2** | ½ (hairline) | focus-ring offset, divider inset only |
| `spacing-2x-small` | 0.25 | **4** | ✓ | icon↔label gap, chip inner |
| `spacing-x-small` | 0.5 | **8** | ✓ | control inner padding, badge padding |
| `spacing-small` | 0.75 | **12** | ✓ | field gap (compact), card inner (compact) |
| `spacing-medium` | 1 | **16** | ✓ | card body padding, field gap (comfortable), gutter |
| `spacing-large` | 1.5 | **24** | ✓ | section gap, page margin, group separation |
| `spacing-x-large` | 2 | **32** | ✓ | major section gap |
| `spacing-2x-large` | 3 | **48** | ✓ | page top padding (desktop) |
| `spacing-3x-large` | 4 | **64** | ✓ | empty-state vertical centering |

> Create these as **Figma Number Variables** in a collection `spacing/*`. Bind component padding/gap to the variable, not a literal — this is what makes density modes a single-variable swap (§5).

### 1.3 Type scale (SLDS font tokens → Arial fallback per brand guide)

| Token | px / line-height | Weight | Use |
|---|---|---|---|
| `font-size-1` | 10 / 16 | 400 | micro-labels, table superscript |
| `font-size-2` | 12 / 16 | 400/600 | field labels, captions, badges, help text |
| `font-size-3` | 13 / 20 | 400 | table cell, secondary body |
| `font-size-4` | 14 / 20 | 400/600 | body, input value |
| `font-size-5` | 16 / 24 | 600 | card title (`h2`) |
| `font-size-6` | 18 / 28 | 600 | page/object title (`h1`) |
| `font-size-7` | 20 / 28 | 700 | stat-tile numbers |
| display | 30 / 36 | 700 | resolve-banner big count |

Font family: heading `"Alright Sans", Arial, sans-serif`; body `Arial, sans-serif` (digital fallback per brand guide). Line-heights are 4px multiples.

### 1.4 Color (bind to brand Variables, default IBX)
Map the semantic tokens from `brand-tokens.css` into a Figma color Variable collection with two **modes**: `IBX` (default) and `AmeriHealth`. Components reference semantic names only.

| Semantic Variable | IBX | AmeriHealth |
|---|---|---|
| `brand` (actions/links) | `#007DB6` | `#012169` |
| `brand-pure` (logo fills) | `#008CCC` | `#012169` |
| `brand-dark` (hover/headers) | `#024D76` | `#00164A` |
| `brand-light` (selected/tint) | `#E6F4FB` | `#E6EBF3` |
| `success / success-bg` | `#4D8B3F` / `#E3F1DD` | `#2E7D52` / `#E0F0E8` |
| `warning / warning-bg` | `#F16935` / `#FDE7DC` | `#C2691A` / `#FBE9D8` |
| `error / error-bg` | `#EA1D2C` / `#FDE3E5` | `#C1272D` / `#FBE3E4` |
| `qc-accent / qc-bg` | `#924799` / `#F1E9F3` | `#AF1685` / `#F7E9F3` |
| neutral: `text / text-muted / border-light / surface-alt` | `#181818` / `#747474` / `#ECEBEA` / `#FAFAF9` | same |

### 1.5 Radius, elevation, hit area
- `radius`: 4px (controls, cards, chips), 999px (pills/avatars). One radius Variable `radius-medium = 4`.
- Elevation: card `0 2px 6px rgba(0,0,0,.08)`; modal `0 4px 16px rgba(0,0,0,.16)`; sticky footer `0 -2px 6px rgba(0,0,0,.06)`.
- **Min touch target 44×44px** at `small`/`x-small` breakpoints (WCAG 2.5.5 / SLDS mobile). At desktop, 32px control height is acceptable for pointer.

---

## 2. Figma file structure

```
📄 Page 01 · Foundations      → spacing scale, type, color modes, grid, density tokens (import the SVG)
📄 Page 02 · Components        → every component below, as a Component Set with Variants
📄 Page 03 · Screens           → 5 step frames × {Comfortable, Compact} × {Desktop, Tablet, Mobile}
📄 Page 04 · Prototype + Redlines → flow wiring + Dev-Mode spacing annotations
```

**Naming convention (matches LWC bundle names for clean Figma→LWC handoff):**
`mau / <Section> / <Element> — <Variant>`
e.g. `mau / ReviewGrid / Row — Comfortable·Bundle`, `mau / Field / TextInput — Compact·Error`.
Frames: `Screen / 1-Identify — Desktop·Comfortable`.

---

## 3. Component library (auto-layout + token-bound)

Every component is **Auto Layout**. "Pad" = padding token, "Gap" = item-spacing token. All values reference §1.2 Variables.

### 3.1 App Header (global nav bar)
- Auto Layout **horizontal**, Pad `x-small 16`/`y x-small 8`, Gap `small 12`, Fill `linear var(--header-from→--header-to)`, height **40**.
- Children: waffle (16), brand wordmark (`font-2`, 700, #fff), breadcrumb (`font-2`, brand-light text), spacer (fill), brand-switch segmented (IBX/AmeriHealth — prototype only), global search (pill, width 320, hug→fill ≤medium), avatar (28 circle).
- Resize: search collapses to icon at `medium`; breadcrumb hidden at `small`.

### 3.2 Object Header (page header)
- Auto Layout horizontal, Pad `medium 16`/`y small 12`, Gap `small 12`, Fill surface, bottom border `border-light 1`.
- Icon tile 34×34 r6 `brand-pure`; title block (eyebrow `font-2` muted uppercase, h1 `font-6`); spacer; "Help" link `font-2` brand.

### 3.3 Progress Path (SLDS Path) — `mau / Path`
- Auto Layout horizontal, Gap `none` (chevrons overlap −10), Pad `medium 16`/`y small 12`.
- **Node** Component Set, Variants: `state = {todo, active, done}` × `density = {comfortable, compact}` × `kind = {step, qc}`.
  - Node Auto Layout horizontal, Pad `x-small 16`/`y x-small 8` (comfortable) → `x-small 12`/`xx-small 4` (compact); Gap `xx-small 4`; chevron clip; height 36 (comfortable) / 28 (compact).
  - Fills: todo `surface-alt`/muted text; active `brand`/#fff; done `success-bg`/success; qc node uses `qc-bg`/`qc-accent` (active `qc-accent`/#fff).
- Responsive (§6): at `small` swap to **Stepper** variant — dots + "Step 2 of 5 · Review" label.

### 3.4 Card — `mau / Card`
- Auto Layout vertical, Gap `none`, Fill surface, border `border-light 1`, r4, elevation card, margin-bottom `medium 16`.
- **Card Header** sub-component: Pad `medium 16`/`y small 12`, Gap `x-small 8`, bottom border; h2 `font-5`, optional `.sub` `font-2` muted, spacer, optional action.
- **Card Body**: Pad **`medium 16`** comfortable / **`small 12`** compact.

### 3.5 Form Field — `mau / Field` (the density workhorse)
Component Set Variants: `type = {text, select, segmented, textarea}` × `state = {default, focus, error, readonly}` × `density = {comfortable, compact}`.

| Part | Comfortable | Compact |
|---|---|---|
| Label (`font-2`, 600) → control gap | `xx-small 4` | `xx-small 4` |
| Control height | **32** | **28** |
| Control inner pad | `x-small 8` h / `xx-small 4` v | `x-small 8` h / `3x-small 2` v |
| Control → help-text gap | `xx-small 4` | `xx-small 4` |
| Field block → next field (in `formgrid`) | `medium 16` (row) / `large 24` (col) | `small 12` / `medium 16` |

- Focus: border `brand` + 1px ring (offset `3x-small 2`). Error: border `error`, bg `error-bg` tint, help text `error`.
- Required asterisk `error`, `xx-small 4` left of label.

### 3.6 Buttons — `mau / Button`
Variants: `kind = {primary, neutral, outline-brand, icon, destructive}` × `density`.
- Auto Layout horizontal, Pad `medium 16` h / `x-small 8` v (comfortable, height 32) → `small 12` h / `xx-small 4` v (compact, height 28). Gap `xx-small 4` (icon↔label). r4. Label `font-4` 600.
- primary `brand`/#fff (hover `brand-dark`); outline-brand border `brand`/brand text; neutral border `border`/text; icon 32×32 (28 compact); destructive `error`.

### 3.7 Data Table / Review Grid — `mau / DataTable` (highest-value component)
Maps to reused LWC `prmEnhancedDatatable`. Component Set Variants on **Row**: `density = {comfortable, compact}` × `status = {default, selected, bundle, error, deselected}`.

| Part | Comfortable | Compact |
|---|---|---|
| Header row height | 40 | 32 |
| **Body row height** | **44** | **32** |
| Cell pad (h / v) | `small 12` / `x-small 8` | `x-small 8` / `xx-small 4` |
| Checkbox column width | 44 | 36 |
| Cell text | `font-3` (13) | `font-2` (12) |
| Row gap | none (1px bottom border `border-light`) | none |

- **Header**: sticky, Fill `surface-alt`, bottom border `border 1`, label `font-2` 600 muted.
- **Selected** row: Fill `brand-light`. **Bundle** row: 3px inset-left `warning` (box-shadow inset). **Error** row: Fill `error-bg` tint. **Deselected**: opacity 50%.
- **Diff cell** (old→new address): old text strike + muted, `→` glyph muted `xx-small 4` margins, new text `success` 600. Stacks vertically at `medium` and below.
- **Toolbar** (above table): Auto Layout horizontal wrap, Pad `small 12`, Gap `x-small 8`; search input (fill, max 340), divider, filter chips, spacer, summary `font-2` muted.

### 3.8 Filter Chip / Badge / Pill — `mau / Chip`, `mau / Badge`
- Chip: Auto Layout, Pad `small 12` h / `xx-small 4`→`x-small 8` v, Gap `xx-small 4`, r999, `font-2`. States: default `surface-alt`/border; active `brand-light`/brand/border-brand.
- Badge (status): Pad `x-small 8` h / `3x-small 2` v, r999, `font-2` 600, Gap `xx-small 4`. Variants: `active`(success), `bundle`(warning), `same`(neutral), `new`(brand-light), `error`(error), `verified`(success), `pending`(neutral), `flagged`(warning).

### 3.9 Alerts / Inline Notices — `mau / Alert`
- Auto Layout horizontal, Pad `small 12` h / `x-small 8`→`small 12` v, Gap `x-small 8`, r4, 1px border (semantic @40% tint). Variants `info`(brand), `warning`, `success`, `qc`(qc-accent). Icon `font-5` top-aligned.

### 3.10 Resolve Banner — `mau / ResolveBanner` (Step 2 / QC summary)
- Auto Layout horizontal, Pad `medium 16` h / `small 12`→`medium 16` v, Gap `large 24`, Fill `brand-light` (QC: `qc-bg`), border 1 @25% brand, r4.
- Stat cluster: big number `display`(30) brand-dark + label `font-2` muted; vertical rule (`vr`, 1px×38 @30% brand) `none` gap between clusters. Wraps to 2×N grid at `medium`.

### 3.11 Sticky Action Footer — `mau / Footer`
- Auto Layout horizontal, Pad `medium 16` h / `small 12` v, Gap `medium 16`, Fill surface, top border, elevation footer, **pinned bottom** (Figma: constraint bottom + fixed-on-scroll in prototype).
- Recap text `font-3` left; spacer; buttons right. At `x-small`: stack vertical, buttons full-width (Hug→Fill).

### 3.12 Modal — `mau / Modal` (Address Validation + Confirm)
Maps to reused `addressValidationModal` / `prmGenericConfirmModal`.
- Backdrop 40% black. Dialog: width 480 (`small`+), full-width sheet at `x-small`; Auto Layout vertical; Header Pad `medium 16`; Body Pad `medium 16`, Gap `small 12`; Footer Pad `medium 16` right-aligned buttons.
- Address-validation body: two selectable tiles (Original / Standardized), each a Card-sm, Gap `small 12`, selected = `brand` border + `brand-light`.

### 3.13 Progress (Step 4) — `mau / JobProgress`
- Progress bar: height 12, r999, track `border-light`, fill `linear(brand→brand-accent)`, Gap `small 12` to caption (`font-2` muted).
- **Stat tiles**: 4-up CSS-grid (Auto Layout horizontal wrap, Gap `small 12`); tile = Card-sm, Pad `small 12`, centered; number `font-7`(20–24) semantic-colored, label `font-1`(10–11) uppercase muted. Collapses 4→2→1 across breakpoints.

### 3.14 Notes / Reason field — `mau / Notes`
Maps to `prmNotesCapture`. Textarea Field variant, min-height 56 (comfortable) / 44 (compact), `font-4`, required, char-count `font-1` bottom-right.

---

## 4. Screen layouts (assemble from components)

Each screen = a Figma Frame with vertical Auto Layout: `Header → Path → Page(maxW 1340, centered, Pad large 24) → Footer`. Token annotations in **[brackets]**.

### Step 1 — Identify (`Screen / 1-Identify`)
```
Card "Identify the Group"              [body pad medium16]
  formgrid 2-col [col-gap large24, row-gap medium16]
    Field TaxID*  | Field GroupNPI*
    Field GroupName(readonly) | Field StatusFilter(select)
Card "What to update?"
  Segmented(Billing|Mailing|Both) [pad medium16, gap none]
  BillingBlock: formgrid 3-col [row-gap medium16] · Line1 spans 2 cols
  MailingBlock (conditional)  [section gap large24, top divider dashed]
  Alert info "Precisely validation" [mt medium16]
Footer: Back(disabled) · "Resolve Locations →"(primary)
```

### Step 2 — Review Grid (`Screen / 2-Review`)
```
Card → ResolveBanner [pad y small12]  (1,284 resolved · selected · bundle · matches)
Alert warning "37 bundle members" [mb medium16]
Card
  Toolbar [pad small12, gap x-small8]  search · chips · summary
  DataTable  rows=Comfortable·{default/bundle/selected/error}  [row 44]
  Legend [pad x-small8 small12, gap large24, font-1]
Footer: ← Back · "Continue to Confirm →"(primary)
```
**2-pane note:** when a detail/side-editor is shown (e.g. inline address edit), use a horizontal Auto Layout `grid-pane (fill) | editor-pane (480 fixed)`; editor becomes slide-over ≤`medium` (§6).

### Step 3 — Confirm (`Screen / 3-Confirm`)
```
Card "Confirm the mass update"
  formgrid 2-col [row-gap medium16]  (group · action type · counts · bundle count)
  Field new-address(full)
  Alert info "One QC case + N CMA records"
  Alert success "Records go Active on update"
  Alert warning "37 bundle → Provider Contracting child case"
  formgrid: EffectiveDate · BatchSize · Notes(full, required)
  Checkbox authorize [gap x-small8]
Footer: ← Back · "Submit Mass Update"(primary)
```

### Step 4 — Progress (`Screen / 4-Progress`)
```
Card "Mass update in progress"
  ProgressBar + caption [gap small12]
  StatTiles 4-up [gap small12, mt medium16]   Updated·Bundle→Contracting·Errors·In-progress
  Alert success "QC case 00012977 created · 1,272 CMA records"
  Alert info "Safe to leave · email summary"
  Disclosure "Errors (3)" → mini DataTable
Footer: Start Another · Download CSV · "Open QC Case →"(primary)
```

### Step QC — Verification (`Screen / QC-Review`) — QC persona, qc-accent theme
```
Card(header qc-bg) "QC Verification — Case 00012977"
  ResolveBanner(qc) [1,272 assoc · verified · bundle · errors]
Alert info(qc) "Each row = PRM_CaseManagerAssociation__c"
Card
  Toolbar  search · chips(Pending/Verified/Bundle/Errors) · Verify-selected · Flag-selected
  DataTable rows  cols: Assoc# | PL | PL# | Old→New | Record | QC Verdict
Footer: ← Back · "Send flagged to PDA" · "Approve & Close Case"(primary)
```

---

## 5. Density modes (single-variable swap)

Implement as a Figma **Variable mode** `density = {comfortable, compact}` on the spacing collection, **plus** a `density` Variant property on each Component Set. Switching the page's density mode (or the component variant) re-bound these tokens:

| Aspect | Comfortable (default) | Compact | Rule |
|---|---|---|---|
| Card body padding | `medium 16` | `small 12` | −1 step |
| Field control height | 32 | 28 | −4px |
| Field row gap | `medium 16` | `small 12` | −1 step |
| Form col gap | `large 24` | `medium 16` | −1 step |
| Table body row | **44** | **32** | fixed pair |
| Table cell pad (v) | `x-small 8` | `xx-small 4` | −1 step |
| Button height | 32 | 28 | −4px |
| Path node height | 36 | 28 | fixed pair |
| Section gap | `large 24` | `medium 16` | −1 step |

**Governing rule:** *Compact = drop every spacing token exactly one step on the §1.2 scale; drop fixed control heights by 4px; table rows use the fixed 44/32 pair.* This keeps everything on the 4px grid and makes the two modes provably consistent. Default UI = Comfortable on desktop; force Compact at `medium`↓ (§6).

---

## 6. Responsive breakpoints (annotate on Page 04)

SLDS/Lightning breakpoints. Create one Frame per screen at the three primary widths; annotate behavior with Dev-Mode notes.

| Token | Width | Frame width to draw | Grid cols | Density |
|---|---|---|---|---|
| `x-small` | 0–479 (phone) | **360** | 4 | Compact (forced) |
| `small` | 480–767 | 480 | 6 | Compact |
| `medium` | 768–1023 (tablet) | **768** | 8 | Compact (forced) |
| `large` | 1024–1279 (desktop) | **1280** | 12 | Comfortable (default), user-toggle |
| `x-large` | 1280+ (wide) | 1440 | 12 | Comfortable, content max-width 1340 |

### Per-component responsive annotations

| Component | `large` / `x-large` | `medium` (tablet) | `small` / `x-small` (phone) |
|---|---|---|---|
| **Layout shell** | page max-width 1340, margin `large 24` | margin `medium 16` | margin `small 12`, full-bleed cards |
| **Grid + side editor** | side-by-side (`fill` + `480` fixed) | editor → **slide-over** sheet (480, overlay) | editor → **full-screen** modal |
| **Form `formgrid`** | 3-col (address) / 2-col | 2-col | **1-col** stack |
| **Progress Path** | full labeled path | full path, Compact node | **Stepper**: "Step 2 of 5 · Review" + dots |
| **DataTable** | full 7-col table, sticky header | hide low-priority cols (PL#, phone); horiz-scroll the rest | **transform to Card list** — each row → stacked card (label:value pairs, action menu); no horizontal scroll |
| **Toolbar** | inline (search + chips + summary) | wrap to 2 rows | search full-width row 1; chips horizontal-scroll row 2 |
| **ResolveBanner** | single row of stat clusters | wrap to 2×N | 2×2 stat grid, hide vertical rules |
| **StatTiles (Step 4)** | 4-up | 2-up | 1-up stacked |
| **Sticky Footer** | recap left + buttons right | recap hidden, buttons right | **buttons stack full-width**, primary on top |
| **Modal** | 480 centered dialog | 480 centered | full-width bottom sheet |
| **Touch targets** | 32px controls OK (pointer) | **44px min** | **44px min**, increase tap padding |

> **DataTable → Card transform (annotate explicitly):** below `medium`, a 7-column comparison table is unusable. The Figma annotation on the table frame must read: *"≤ small: render each row as `mau / DataTable / RowCard` — Auto Layout vertical, Pad `small 12`, Gap `xx-small 4`; checkbox + PL name as title row; Old→New stacked; status badge; overflow `⋮` for row actions."* Provide that `RowCard` as its own Variant.

---

## 7. Accessibility & redline notes (Page 04)
- Contrast: all text on brand uses the **accessible** brand `#007DB6` (IBX) / navy (AH), verified ≥ 4.5:1; never the pure logo blue on text.
- Focus order documented per screen; visible focus ring (`brand`, offset `3x-small 2`).
- Status is never color-only: badges carry text + (optional) icon; bundle rows have the inset bar **and** the "⚠ Bundle" badge.
- Annotate every gap/padding with its token name in Dev Mode (e.g. `gap: spacing-medium (16)`), so engineering reads tokens, not pixels.
- Hit areas ≥ 44px at touch breakpoints.

---

## 8. Component → reuse mapping (for the Figma→LWC step)
The MCP `lwc` Figma tools convert Figma → LWC. Naming each Figma component after its LWC bundle makes `get_component_subtree` produce clean output:

| Figma component | LWC bundle (existing/new) |
|---|---|
| `mau / DataTable` | `prmEnhancedDatatable` (reuse) |
| `mau / Field / *`, `mau / Notes` | `prmGenericSearchInput`, `prmNotesCapture` (reuse) + `lightning-input/-combobox` |
| `mau / Modal — AddressValidation` | `addressValidationModal` (reuse) |
| `mau / Modal — Confirm` | `prmGenericConfirmModal` (reuse) |
| `mau / Path`, `mau / JobProgress` | **new** `prmMauPath`, `prmMauProgress` |
| `Screen / 2-Review`, `Screen / QC-Review` | **new** `prmMauReviewGrid`, `prmMauQcReview` |
| container | **new** `prmMassAddressUpdate` |

---

*Deliverables: this spec + `MassAddressUpdate_Figma_Foundations.svg` (drag into Figma's Foundations page as the starting frame).*
