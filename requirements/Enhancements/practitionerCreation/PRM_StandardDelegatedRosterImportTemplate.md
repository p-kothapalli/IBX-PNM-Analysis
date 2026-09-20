# PRM Standard Delegated Roster Import Template

**Date:** 2026-08-04
**Status:** Draft for team review
**Artifact:** `PRM_StandardDelegatedRosterImportTemplate.xlsx` (this folder)
**Companion:** `PRM_DelegatedRoster_CommonSchema.md` (the orchestrator JSON this template maps to)

## Purpose

One **standard vendor-facing import template** that (a) **declares what the update is** via a
controlled `Request Type` column, and (b) can carry **every variation of change** seen across the
12 real vendor files + 4 recent cases — create, add, add-to-all, remove/term, network term, group
create, and demographic/specialty/group/TIN/address changes — in a single file.

**Grounded on:**
- The IBX draft **`1.21.26 External Delegated Provider Import Template_DRAFT`** — its 91-field
  `Data Template (2)` block and `Mapping` (field dictionary) sheet are **reused verbatim** as the
  data block, so existing regulatory/field-dictionary work still applies.
- `PRM_DelegatedRoster_CommonSchema.md` — the operation catalog + 4 termination scopes.
- The 12 source roster files (Minute Clinic, Cooper ×4, Virtua, Jeffcare, NovaCare, UPHS,
  Princeton, Vista, HMH).

## What was wrong with the draft template

The draft's only directive is a **free-text `Comments` column** — the exact ambiguity that makes
every vendor file parse differently. It is also **wide** (3 inline affiliation blocks) and has no
way to express remove / network-term / field-change / new-group. The standard template fixes this
**additively**: it keeps every draft field and only **prepends a control block**.

## Structure

**One row = one operation.** A provider at N locations = N rows; add + remove in the same file =
different rows. Two column blocks:

### A. Control block (NEW — "what is the update") — 15 columns
| Field | Purpose |
|---|---|
| **Request Type** *(dropdown, required)* | Controlled operation — drives all routing/validation |
| Request Notes | Free-text (the old `Comments`) — context only, never parsed |
| Termination Scope *(dropdown)* | `AFFILIATION` \| `GROUP` \| `CONTRACT` \| `NETWORK` |
| Termination Date | Term date (distinct from Effective Date) |
| Termination Reason | e.g. "Group leaving Princeton PO" |
| Network(s) | Network name/code to ADD or TERM (e.g. "Amerihealth PPO Medicare / 2181") |
| Change Field / Old Value / New Value | For `CHANGE_*` — the field + old→new pair |
| Practitioner Ref | Existing IBX id (PIE/BSPA) or `CREATE` |
| Group Ref | Existing IBX id (PIE/BSPA) or `CREATE` |
| Practice Location Ref | Existing IBX id (PIE) or `CREATE` (new address) |
| Vendor Ref | Vendor PIE id or TIN |
| Contract / PO | Contract/PO the row applies to |
| Group Parent | For `CREATE_GROUP` — hierarchy parent (med-svc entity) |

### B. Data block (reused verbatim from the IBX draft) — 91 columns
`Comments, Specialty, Last Name … Provider NPI, Taxonomy 1/2, DOB, Gender, affiliation/appt/creds,
Legal Business Name, Effective Date, TIN, Group NPI/Name, address, billing, Languages, Malpractice
1–2, Board 1–2, PA License/DEA, Education, Residency 1–3, Foreign Residency, Provider Number/PAR,
Concierge, Race, Cultural Competency, Accepting new patients?`

## Request Type vocabulary (the `Request Type` dropdown)

| Request Type | Meaning | Replaces (vendor directive examples) |
|---|---|---|
| `CREATE_PROVIDER` | New practitioner (± new group/location) | Jeffcare/Virtua "Create new provider…"; Cooper "Add as a New Provider" |
| `CREATE_GROUP` | New vendor group/TIN (+ optional parent) | UPHS "New Group" |
| `ADD_TO_LOCATION` | Existing provider → affiliation at existing/new address | "Link provider to group location #N"; Cooper "add to location"; UPHS "Add Location"; Virtua "add to TIN" |
| `ADD_TO_ALL_LOCATIONS` | Affiliate to every active vendor location | Minute Clinic "all locations"; NovaCare "ADD TO ALL LOCATIONS" |
| `REMOVE_FROM_LOCATION` | End an affiliation (scope AFFILIATION/GROUP/CONTRACT) | Cooper "remove from location"; Vista "Term provider…"; Princeton "Terminate PROVIDER/GROUP" |
| `TERM_NETWORK` | End ONE network membership; affiliation stays | HMH "term 1 network" (Amerihealth PPO Medicare / 2181) |
| `CHANGE_DEMOGRAPHIC` | Name/gender/etc. change (old→new) | Cooper "Change Last Name from X to Y" |
| `CHANGE_SPECIALTY` | Specialty/taxonomy change | Cooper "Change Specialty from X to Y" |
| `CHANGE_GROUP` | Relink to a different Group NPI | Cooper "Change group npi from X to Y" |
| `CHANGE_TIN` | Change the TIN | Cooper "Change tin id from X to Y" |
| `CHANGE_ADDRESS` | Update location address/suite | Cooper "Update location from Ste 503 to Ste 505" |

## How every source file collapses into one template

| Source | Old directive | Standard row(s) |
|---|---|---|
| Minute Clinic / NovaCare | "all locations" sentinel | `ADD_TO_ALL_LOCATIONS` |
| Cooper (mixed) | `IBX Comments` + `COMMENTS` | `ADD_TO_LOCATION` / `REMOVE_FROM_LOCATION` / `CHANGE_*` per row |
| Virtua / Jeffcare | free-text "Comments" | `CREATE_PROVIDER` / `ADD_TO_LOCATION` (+ `locationMatch=NEW_ADDRESS`) |
| UPHS | `Type of Request` | `CREATE_GROUP` / `ADD_TO_LOCATION` |
| Princeton | "Terminate PROVIDER/GROUP … contract" | `REMOVE_FROM_LOCATION`, scope `CONTRACT`/`GROUP` |
| Vista | "Term provider from group and location" | `REMOVE_FROM_LOCATION`, scope `AFFILIATION`/`GROUP` |
| HMH | Medicare flag + network 2181 | `TERM_NETWORK`, scope `NETWORK` |

## The .xlsx has 3 sheets
1. **Import Template** — control block (blue) + data block (green), frozen header, `Request Type`
   & `Termination Scope` dropdowns, and 5 worked example rows (ADD, CREATE_GROUP, REMOVE/contract,
   TERM_NETWORK, CHANGE_TIN).
2. **Request Types** — the controlled vocabulary + required fields + directive phrases it replaces.
3. **Field Dictionary** — control-block definitions + which Request Types each field applies to
   (data-block dictionary continues to live in the draft's `Mapping` sheet).

## Open questions (same as the schema doc)
1. `TERM_NETWORK` needs its own backend lane (end `HealthcareFacilityNetwork` only, not the affiliation).
2. Is the `CHANGE_*` family in scope for v1? (~15–20% of Cooper rows.)
3. Flag/query-driven files (HMH) — supported via a file-level constant `Request Type` + `Network(s)` selection.
4. Model Contract/PO as first-class, or fold into group/TIN?
5. `lastManStanding` default — AUTO vs analyst-confirm.
