# USER STORY: Ancillary Guided Flow — Preserve Address Data When Navigating Back to Provider Information

**Persona:** Ancillary Cred Specialist
**Priority:** P0 (data-loss defect blocking clean submissions)
**OmniScript:** `PRM_AncillaryProviderForm_English` (active version **v43**)
**Integration Procedures:** `PRM_PrepareAncillaryAddressScreenData`
**Relevant Requirements:** UAT Bug #1197090

---

## Story

**As an** Ancillary Cred Specialist,
**I want** the address details I enter on the Address screen to stay intact when I go back to the Provider Information screen and return,
**So that** I never have to re-key an entire address just because I revisited an earlier step, and my submission cannot silently lose data I already captured.

**Why it matters:** Today, every trip back to Provider Information wipes the entire Address screen, forcing full re-entry and risking incomplete or inconsistent submissions. It reproduces 100% of the time on both IBC and AmeriHealth ancillary applications, so it directly slows down every multi-step ancillary intake.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|---------------|-------------|
| Ancillary Assessment / Provider Creation | `PRM_AncillaryProviderForm_English` (v43) | `Addresses` (entry) ↔ `Provider` (Provider Information) | `PRM_PrepareAncillaryAddressScreenData` IP pre-fills the `Addresses` node from the provider/group record |

---

## Current State (from codebase)

- The Provider Information screen (`Provider` step) and the Address screen (`Addresses` step) are separated by the `PRM_PrepareAncillaryAddressScreenData` Integration Procedure Action (sequence 5.0, between step 1.0 `Provider` and step 7.0 `Addresses`).
- The `Addresses` step stores all user-entered address input (Physical, Billing, Mailing/Correspondence, Corporate/Hospital Affiliation, additional locations) under the `Addresses` data node.
- `PRM_PrepareAncillaryAddressScreenData` rebuilds the address list purely from the provider/group record, returns it as an `Addresses` object, and — because the action has **no execution guard** and writes its response back with an **empty response path** — it **overwrites the `Addresses` node on every forward navigation**.
- **Net effect:** `Addresses → Next → Address Validation → Previous → Provider → Next` re-runs the prep and discards everything the Ancillary Cred Specialist typed.
- The post-validation Set Values (`ValidatedAddressData`, `SetChangedAddress`) act on a different node (`AncillaryAddress` / `ValidatedAddress`) and are **not** part of this wipe.

---

## Acceptance Criteria

**AC-1 — Address data is retained on back-and-forward navigation**

**Given** an Ancillary Cred Specialist has entered address details on the Address screen and moved forward to the Address Validation screen,
**When** they navigate back to the Provider Information screen and then return to the Address screen without changing the selected group/vendor,
**Then** every address field they previously entered is still populated exactly as they left it (Physical, Billing, Mailing/Correspondence, Corporate/Hospital Affiliation, phone, zip+4, contact person).

**AC-2 — First-time address pre-fill still works**

**Given** an Ancillary Cred Specialist reaches the Address screen for the first time in a submission,
**When** the Address screen loads,
**Then** the addresses are pre-filled from the selected provider/group record exactly as they are today.

**AC-3 — Changing the group refreshes the addresses**

**Given** an Ancillary Cred Specialist has already visited the Address screen for one group/vendor,
**When** they go back to Provider Information, select a **different** group/vendor, and return to the Address screen,
**Then** the addresses are re-pre-filled to reflect the newly selected group/vendor rather than showing the previous group's addresses.

**AC-4 — New group (no existing group on file) preserves typed data**

**Given** an Ancillary Cred Specialist is submitting for a brand-new group/vendor that has no existing group record,
**When** they enter addresses, move forward, then return to the Address screen without changing the group,
**Then** their typed addresses are preserved and are not reset to blank.

**AC-5 — Submitted addresses match what the specialist reviewed (no regression)**

**Given** an Ancillary Cred Specialist has completed the Address and Address Validation screens and reaches the Review screen,
**When** they submit the ancillary application,
**Then** the addresses saved on the created records match exactly what was shown on the Review screen, with no loss or reversion to pre-filled defaults.

**AC-6 — Multiple locations and "same as physical" choices are retained**

**Given** an Ancillary Cred Specialist has added multiple office locations and toggled "Billing/Mailing same as Physical",
**When** they navigate back to Provider Information and return to the Address screen,
**Then** all additional locations and the same-as-physical selections remain intact.

---

## Technical Implementation (high-level)

Guard the address-prep action so it runs **once per group selection** instead of on every forward pass; track the prepared group with an OmniScript-only marker. No IP/DataRaptor/Apex logic changes.

| Component | Type | Change | Notes |
|---|---|---|---|
| `PreparedForGroupId` (new) | New OmniScript element (hidden Text) in the `Provider` step | Add hidden field, `defaultValue = "__NOTPREPARED__"`, `hide: true`, `required: false` — remembers the group the Address screen was last prepared for | Sentinel guarantees first-entry prep. Drives AC-1, AC-3, AC-4 |
| `PRM_PrepareAncillaryAddressScreenData` | Modified OmniScript IP Action (seq 5.0) | Set Conditional View (`show`) to run only when `Provider:PreparedForGroupId` ≠ `%Provider:GroupTypeAhead-Block:ExistingGroupId%` | Prevents the re-seed/overwrite on unchanged round-trips. Drives AC-1, AC-2, AC-3 |
| `SV_MarkAddressPrepared` (new) | New OmniScript Set Values (insert seq 5.5, before `Addresses` step) | Set `PreparedForGroupId = %Provider:GroupTypeAhead-Block:ExistingGroupId%` after the prep action | Keeps the marker in sync; harmless re-affirm on skip. Drives AC-1, AC-3 |
| `vlocity_export/OmniScript/PRM_AncillaryProviderForm_English/*` | DataPack JSON mirror | Mirror the three changes above in the exported element JSONs | Keep repo export in sync with `.os-meta.xml` |

**Files:** `force-app/main/default/omniScripts/PRM_AncillaryProviderForm_English_43.os-meta.xml` (+ matching `vlocity_export` element JSONs).

**Fallback (if group-change refresh is out of scope, AC-3 dropped):** guard the prep action to run only when the `Addresses` node is empty. Simpler, but will not refresh addresses when the group changes — the group-id guard above is preferred.

**Deploy:** metadata-only. `sf project deploy start --metadata "OmniProcess:PRM_AncillaryProviderForm_English_43"` then clear the OmniStudio/Vlocity platform cache. Rollback: revert the `show` guard to `null` and remove the two new elements.

---

## Definition of Done

- [ ] Hidden `PreparedForGroupId` element added to the `Provider` step with the sentinel default.
- [ ] Conditional View guard added to `PRM_PrepareAncillaryAddressScreenData`.
- [ ] `SV_MarkAddressPrepared` Set Values added after the prep action, before the `Addresses` step.
- [ ] `.os-meta.xml` and `vlocity_export` element JSONs are consistent.
- [ ] AC-1 through AC-6 pass in a sandbox for both IBC and AmeriHealth form types.
- [ ] Merge-path of the guard verified in OmniScript Designer at runtime.
- [ ] Regression: Address Validation (Precisely), Review, and final submission (`CreateAncillaryFormRecords`) unaffected; submitted addresses match Review.
- [ ] Deployed to the active v43 and platform cache cleared.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | When the specialist changes the group after entering custom addresses, is a full re-pre-fill (wiping custom edits for the new group) the desired behavior? | Determines whether AC-3 re-seeds or merges | BA / Product |
| 2 | Should the guard also refresh addresses if provider fields **other than group** change (e.g., NPI, taxonomy)? | Widens/narrows the guard condition | Technical / BA |
| 3 | Is confirming the fix on active v43 in place acceptable, or must it be a new version (v44)? | Deployment path | Technical / Release |
| 4 | Any read-only / resubmission scenarios (e.g., re-opened application) where prep must always re-run? | Additional guard exceptions | BA / Ops |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_AncillaryProviderForm_English` (v43) | OmniScript | HIGH | Adds guard + marker; changes when address prep executes |
| `PRM_PrepareAncillaryAddressScreenData` | Integration Procedure | LOW | No internal change; only gated on execution by the OmniScript |
| Address Validation / Review / Submission chain | IP / OmniScript steps | LOW | Behavior unchanged; validated by regression ACs |
| Downstream record creation (`CreateAncillaryFormRecords`) | Integration Procedure | LOW | No change; addresses now reflect user input reliably |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-------------|--------|-------|
| `PreparedForGroupId` hidden field | OmniScript element (new) | S | Single hidden Text element with default |
| `PRM_PrepareAncillaryAddressScreenData` guard | OmniScript element edit | M | Add + validate Conditional View merge-path |
| `SV_MarkAddressPrepared` | OmniScript element (new) | S | Single Set Values |
| QA (both branches, 6 ACs) | Test | M | IBC + AmeriHealth, back/forward + group-change |

**Total Estimated Effort:** ~M (≈ half a day incl. QA) — *AI-estimated, validate with team.*
