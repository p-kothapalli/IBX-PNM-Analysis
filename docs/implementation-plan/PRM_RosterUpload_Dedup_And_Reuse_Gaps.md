# PRM Roster Upload — Duplicate-Handling & Record-Reuse Gaps

**Status:** Analysis / not yet implemented
**Last updated:** 2026-07-02 — added §7–§9: three real vendor files (Cooper / NovaCare / Jeffcare) checked against the guided flow
**Companion docs:** `PRM_RosterUpload_PhaseI_Prompt.md`, `PRM_RosterUpload_ComponentTracker.md`, `PRM_RosterUpload_Einstein_Mapping_Plan.md`

---

## 1. Problem statement

The roster upload feeds the canonical `{ messageHeader, practitioners[] }` envelope into the
async framework (`PRM_JsonJobUploadService.process` → E1 `PRM_CaseService` → E2–E11 batches →
team's `PRM_PracticeLocationAndGroupBatch`). Every creation step currently does a **blind
insert** with **no "does this already exist?" check**.

Observed failures (job `AJ-0000310` and its re-submit):

| Error | Object / field | Where |
|---|---|---|
| `DUPLICATE_VALUE, duplicates value on record 001Ov00001u6DWqIAM` | `Account.HealthCloudGA__SourceSystemId__c` (Individual NPI, **unique external id**) | E1 `PRM_CaseService` blind `insert` |
| `DUPLICATE_VALUE ... identifier already exists (0hkOv…)` | `Identifier` (EIN / CAQH) | step 2 `PRM_PracticeLocationAndGroupBatch` |
| `REQUIRED_FIELD_MISSING: [Name]` | practice-location Name | step 2 (fixed for practiceName via group-name fallback) |

Root cause: the roster path was built as **create-only**. Real delegated rosters routinely
contain practitioners / groups / locations that **already exist**, so the flow must
**match-then-reuse**, not re-create.

## 2. The reference rule (how Participation / Creation already does it)

The guided flows never blind-insert. They resolve existing records first and reuse the Id.

- **Group reuse** — `PRM_PractitionerCreationHelper.getUniqueAccountForNPITaxId(npi, taxId)`
  matches on **Tax ID (active `Identifier` EIN) + Group NPI** (`HealthcareFacility.PRM_NpiId__r.npi`)
  → returns `ExistingGroupId` / `ExistingGroupNPIId` / `TINID` and reuses them.
- **Practice-location reuse** — `PRM_PractitionerCreationHelper.getlocVsFac(accountId, npi)` /
  `getPracticeLocation(...)` returns existing `HealthcareFacility` + `Address` for the account/NPI.
- **Practitioner reuse** — the OmniScript starts from a practitioner the user **searched and
  selected**, so the existing person Account is reused; the "creation" DataRaptor
  (`DRPAccountCaseCaseManagerCreation`) only fires for a genuinely new practitioner.
- **Effective-date guardrail** — `PRM_PractitionerCreationValidator` fail-fast prechecks
  effective-date overlaps against existing HF/HCPF/HFN **before any DML** (AC5: if anything
  would fail, nothing commits).

The roster is **bulk + unattended**, so it must perform this matching itself for every
practitioner / group / location in the file.

---

## 3. Missing use cases

Severity: **P1** = blocks a clean re-run today · **P2** = data correctness · **P3** = polish.

### 3.1 Practitioner (person Account) — match key: Individual NPI (`HealthCloudGA__SourceSystemId__c`)

| # | Use case | Current behavior | Expected (per reference) | Sev |
|---|---|---|---|---|
| P-1 | Practitioner is brand new | Insert new Account | Create | — |
| P-2 | **Practitioner already exists (same NPI)** | `DUPLICATE_VALUE`, whole job fails | Reuse existing Account; link to new groups/locations; create the Case Manager for this change | **P1** |
| P-3 | Same practitioner on multiple rows in one file (multi-group/location) | Envelope already groups by NPI → one Account attempted | Confirm single Account, correct multi-group nesting | P2 |
| P-4 | Practitioner exists, demographics differ (name/DOB/gender/email) | N/A (fails at P-2) | Decide **update vs. leave** — reference "creation" does not overwrite; "participation" may update select fields | P2 |
| P-5 | Practitioner exists but **inactive / terminated** | N/A | Define reactivation + effective-date behavior | P2 |
| P-6 | Reuse + effective dates | N/A | On reuse, decide whether `PRM_EffectiveFrom__c/To__c` are refreshed or preserved | P2 |
| P-7 | Same NPI, different name in file (data-entry error) | Silently creates/associates | Flag as validation error (client already warns; server should too) | P3 |

### 3.2 Group (business Account) — match key: Group NPI + Tax ID (EIN `Identifier`)

| # | Use case | Current behavior | Expected | Sev |
|---|---|---|---|---|
| G-1 | Group brand new | Insert group Account + NPI + EIN Identifier | Create | — |
| G-2 | **Group already exists (NPI + TIN)** | Duplicate `Identifier` insert → `DUPLICATE_VALUE` | Reuse via `getUniqueAccountForNPITaxId`; do **not** re-create Identifier | **P1** |
| G-3 | **Same group repeats across many rows in one file** | Attempts to create the group/Identifier per row → intra-file duplicate | Create once, reuse for all rows referencing it | **P1** |
| G-4 | Group Name blank | `REQUIRED_FIELD_MISSING [Name]` | Required-field validation before submit | P2 |
| G-5 | Tax ID formatting differences (`22-2170196` vs `222170196`) | Exact-string match may miss existing | Normalize before match | P2 |
| G-6 | Same Group NPI under two Tax IDs (or vice-versa) | Ambiguous | Define composite-key precedence | P3 |

### 3.3 Practice Location (`HealthcareFacility`) + Address — match key: Account + NPI + Location

| # | Use case | Current behavior | Expected | Sev |
|---|---|---|---|---|
| L-1 | New location | Create HF + Address | Create | — |
| L-2 | Existing location for the group | May duplicate | Reuse via `getlocVsFac` / `getPracticeLocation` | P2 |
| L-3 | Practice Name blank | was `REQUIRED_FIELD_MISSING` | **Fixed** — falls back to group name in `rosterEnvelopeBuilder` | done |
| L-4 | Primary practice location flag | Not deduped | Ensure one primary per practitioner | P2 |
| L-5 | Delegated info-code assignment on reused location | Not handled | Match reference `checkDelegatedPracLoc` | P3 |

### 3.4 Affiliations — `HealthcarePractitionerFacility` (HCPF) + `HealthcareFacilityNetwork` (HFN)

| # | Use case | Current behavior | Expected | Sev |
|---|---|---|---|---|
| A-1 | New practitioner↔location / network link | Create | Create | — |
| A-2 | Affiliation already exists | May duplicate | Reuse / skip | P2 |
| A-3 | Effective-date overlap vs existing HF/HCPF/HFN | Not prechecked on roster path | Port `PRM_PractitionerCreationValidator` fail-fast rule | P2 |

### 3.5 Identifiers & NPI records — `Identifier` (CAQH / EIN), `HealthcareProviderNpi`

| # | Use case | Current behavior | Expected | Sev |
|---|---|---|---|---|
| I-1 | CAQH / EIN Identifier already exists | Duplicate insert → `DUPLICATE_VALUE` | Match on `IdValue + PRM_Type__c + ParentRecordId` (active), reuse | **P1** |
| I-2 | Individual / Group NPI record already exists | May duplicate | Reuse by `Npi + NpiType + PractitionerId` | P2 |

### 3.6 Downstream sub-records (E5–E11) — License / Education / Taxonomy / Board / Language

| # | Use case | Current behavior | Expected | Sev |
|---|---|---|---|---|
| D-1 | License (number + state) already exists | Likely duplicates on re-run | Reuse/update; note controllers already have a "revive errored duplicate" pattern (`PRM_BusinessLicenseControllerHelper`) | P2 |
| D-2 | Education / Taxonomy / Board / Language repeat | Likely duplicates on re-run | Match on natural key, reuse | P2 |

### 3.7 Case / Case Manager (`IndividualApplication`)

| # | Use case | Current behavior | Expected | Sev |
|---|---|---|---|---|
| C-1 | New delegated change for existing practitioner | Blocked (P-2) | Create a **new** Case Manager tracking this change, linked to the reused Account | P2 |
| C-2 | An open Case Manager already exists for the practitioner | Always creates new | Decide reuse-open vs always-new per delegated policy | P3 |

---

## 4. Cross-cutting gaps

1. **Whole-file re-submit is not idempotent.** Re-uploading the same roster should be safe
   (reuse everything), not error. `HealthCloudGA__SourceSystemId__c` is a **unique external id**,
   so an `upsert`-by-external-id strategy is technically available for the Account.
2. **Partial-failure re-run duplicates.** This is exactly what happened: step 2 failed, but E1 +
   step-1 records were already committed. Re-running then collides on those committed records.
   The multi-batch chain **commits per step** (no cross-step rollback), so any mid-chain failure
   leaves partial data that blocks a clean retry.
3. **No cross-transaction rollback (AC5 parity).** The guided flow's fail-fast validator ensures
   "if anything fails, nothing commits." The async chain has no equivalent, so a failed job leaves
   orphaned Accounts/CMs/graph records.
4. **Match-key normalization** (Tax ID dashes, NPI whitespace, name casing) must happen before any
   equality check, or existing records are missed and re-created.
5. **Update-vs-preserve policy on reuse** is undefined for every reused entity (which fields the
   roster is allowed to overwrite on an existing practitioner/group/location).

---

## 5. Where the logic belongs (open decision)

- **E1 `PRM_CaseService`** is the natural home for practitioner find-or-reuse, but it is the
  **shared** service also backing the team's `PRM_JSON_Async_Job_Upload` page. Editing it changes
  behavior for both paths (a strict improvement, but their file).
- **Group / location / identifier reuse** belongs in the team's
  `PRM_PracticeLocationAndGroupBatch` (step 2), reusing `getUniqueAccountForNPITaxId` /
  `getlocVsFac`.
- Alternative: a **pre-resolve step in `PRM_RosterUploadController`** that annotates the envelope
  with existing Ids so only the roster path is affected — but downstream still needs to honor
  those Ids.

**Recommended target state:** the entire chain performs match-then-reuse keyed on the natural
identifiers above, making a full or partial re-submit idempotent, matching the Participation /
Creation flow rules. Requires alignment with the team that owns E1 and the practice-location/group
batch before implementation.

## 6. Match-key quick reference

| Entity | Match key | Reference source |
|---|---|---|
| Practitioner Account | Individual NPI = `Account.HealthCloudGA__SourceSystemId__c` (unique ext id) | `PRM_CaseService` (stamp), guided-flow search |
| Group Account | Group NPI + Tax ID (EIN `Identifier`) | `getUniqueAccountForNPITaxId` |
| Practice Location | Account + NPI + LocationId | `getlocVsFac` |
| Identifier (CAQH/EIN) | `IdValue` + `PRM_Type__c` + `ParentRecordId` (active) | `getAccountForIdentifier` |
| NPI record | `Npi` + `NpiType` + `PractitionerId` | `PRM_PracLocTermHelper`, HCPNpi usage |
| License | LicenseNumber + State | `PRM_BusinessLicenseControllerHelper` |
| **Vendor cross-ref (existence signal)** | Provider/Group **BSPA**, **IBC Prov #**, **Group Number** — when populated the record already exists in IBX | Cooper / NovaCare / Jeffcare source columns (see §7) |

---

## 7. Vendor-file reality check (Cooper / NovaCare / Jeffcare)

Parsed the three real files against the canonical template (`rosterTemplate.js`) and the
guided flow (`PRM_PractitionerParticipationForm`).

| File | Sheet | Rows | Labeled cols | Notes |
|---|---|---|---|---|
| Cooper `…Updates Pg 2 (1).xlsx` | `Updates Pg 2` | 108 | 78 | Widest; carries **SSN** + UPIN + full cred history |
| NovaCare `…Initial Cred received…xlsx` | `6 Rows` | 8 | 27 | Small; clean; `Office Practice Name` present |
| Jeffcare `…Proxy_Email Rec…xlsx` | `JUP.MAHC.vRad 9.11.25 Proxy` | 65 | 96 | Widest cred detail; PA **and** NJ licenses |

### 7.1 The reuse/existence signal is IN the vendor data

The `DUPLICATE_VALUE` problems (§1, §3) are exactly what these columns are meant to prevent —
the vendors already tell us whether a record exists in IBX:

- **NovaCare** — `Practitioner BSPA = "No BSPA number found"` on every row → **all practitioners new** → create.
- **Jeffcare** — `Provider BSPA = "New"` (new practitioner) **but `Group BSPA` populated** (e.g. `004262333`, `002809537`) → **group already exists** → reuse group / do **not** re-create its Identifier (this is the step-2 duplicate). `IBC Prov #` blank → no IBX provider number yet.
- **Jeffcare** — the **same `Provider NPI` repeats across rows** (one practitioner, multiple groups/locations) → intra-file practitioner dedup (ref P-3).
- **Cooper** — no BSPA column; existence must be resolved by **Individual NPI** + **Practitioner PIE** (external case #) and **Group NPI + TIN**.

**Implication:** the dedup design (§3, §6) should treat a populated **BSPA / IBC Prov # / Group
Number** as a first-class "reuse this record" signal in addition to NPI/TIN matching. Absence
(`"New"`, `"No BSPA number found"`, blank) means create.

### 7.2 PHI / PII callout

- **Cooper carries SSN** (e.g. `551-89-6494`) in column `N`, plus DOB. SSN is **not** in the
  canonical template and must be **stripped at parse** and never persisted or sent to any LLM
  (see `PRM_RosterUpload_Einstein_Mapping_Plan.md`). DOB is retained (needed by the flow) but is
  sensitive.

## 8. Field-coverage gaps — vendor supplies + guided flow captures, our envelope drops

These are **model gaps**: the guided flow captures the field (backend supports it) and at least
one vendor supplies it, but the canonical roster envelope has no home for it today.

| Concept | Guided-flow field | Vendor column(s) | In template? | Sev |
|---|---|---|---|---|
| Provider role (PCP vs Specialist) / Title | `PractitionerRole` / `ProviderRole` | Cooper `PCP/ SCP`; Jeffcare `PCP/SPC`, `Title` | ❌ | P2 |
| Board certifications (name/status/date/expiration) | board-cert step | Cooper `BOARD 1..3 …`; Jeffcare `Board Certified 1/2 …` | ❌ (backend E7 exists, unfed) | **P1** |
| DEA registration + expiration | DEA fields | Cooper `NJ DEA (+Exp)`; Jeffcare `PA/NJ DEA (+Exp)` | ❌ | P2 |
| CDS registration + expiration | CDS fields | Cooper `CDS (+Exp)`; Jeffcare `NJ CDS (+Exp)` | ❌ | P2 |
| License **expiration** date | license step | all (`… EXPIRATION` / `Exp Date`) | ⚠️ number+state only, no expiry | P2 |
| Multi-state licenses (PA **and** NJ) | license step (multi) | Jeffcare `PA Medical` + `NJ Medical` | ⚠️ 4 slots, unmapped | P2 |
| Education **type** + specialty + start/finish | education step | Cooper/Jeffcare `Internship / Residency / Fellowship (+ specialty, start, finish)` | ⚠️ institution/degree/grad only | P2 |
| Secondary / alternate specialty | specialty step | Cooper `SECONDARY`/`ALTERNATE SPECIALTY`; Jeffcare 2nd `Specialty` | ⚠️ single `primarySpecialty` | P2 |
| Concierge fee flag | `PractitionerConceirgeFeeQuestion` | Cooper `Concierge Medicine Yes/No` | ❌ | P3 |
| Accessibility (handicap / public transport) | assistive-aid / directory | Jeffcare `Handicapped Accessible`, `Public Transportation Access` | ❌ (→ `PRM_ProviderFeature__c`) | P3 |
| Hospital affiliation | affiliation | Cooper `AFFILIATION`; Jeffcare `Primary Affiliation Hospital` | ❌ | P3 |
| Credentialing / recred dates | committee / dates | NovaCare `InitialAppointment`/`NextAppointment`; Jeffcare `Initial Cred`/`Next Recred`; `Credentialing Committee` | ❌ | P2 |
| Malpractice insurance | malpractice | Cooper `MALPRACTICE INSURANCE COVERAGE` | ❌ | P3 |
| Billing address (distinct from practice) | address block | all (`… BILLING …`) | ⚠️ generic `addresses[]` w/ type only | P2 |
| Department / Section | department | Cooper `DEPARTMENTS`; Jeffcare `Department/Section` | ❌ | P3 |
| Vendor cross-ref IDs (BSPA / IBC Prov # / Group Number) | (drives reuse) | NovaCare/Jeffcare BSPA + `IBC Prov #`; NovaCare `Group Number` | ⚠️ only `sourceLocationId` | **P1** (see §7.1) |
| SSN, UPIN | not stored | Cooper `SSN`, `UPIN NUMBER` | ❌ by design | PHI — exclude |

### 8.1 Source gaps (our template has it, no vendor supplies it)

These guided-flow fields **cannot** be populated from any of the three rosters:

- **CAQH ID** (`PractitionerCAQHID`) — no vendor column → `caqhNumber` stays blank → no CAQH Identifier.
- **Practitioner email** (`PractitionerEmail`) — no vendor column.
- **Telehealth** flags (`telehealthEnabled/Only`) — no vendor column.

## 9. Summary of what changed vs the original gap list

- §3 dedup/reuse gaps are **confirmed by real data**: Jeffcare's populated `Group BSPA` with a
  `"New"` practitioner is the exact shape that produces the practitioner-insert success +
  group-Identifier `DUPLICATE_VALUE`.
- Added **§8 field-coverage gaps** — the vendor files carry substantially more of what the guided
  flow captures (board certs, DEA/CDS, license expiry, education detail, role, cred dates) than the
  Phase I canonical template models. Board certifications (P1) and the vendor cross-ref IDs (P1)
  are the highest-value additions.
- Added **PHI handling** requirement for Cooper SSN.
