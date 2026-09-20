# PDM Manual Update — Capitated Bundle Validation Bug + Practice Location Bundle Search Redesign

**Date:** 2026-05-04
**Org investigated:** `qa-sandbox` (`prashanth.kothapalli@ibx.com.pie.qa`, `00DcW000004drQLUAY`)
**OmniScripts in scope:**
- `PRM_PDMManualUpdate_English` (Update Billing/Mailing Address step)
- `PRM_ManagePracticeLocationBundles_English` → embeds `PRM_SelectPracticeLocationBundle_English`
**DataRaptors in scope:**
- `PRMDRExtractVendorPracticeLocations` (writes `Facility:IsCapitated`)
- `PRMGetPracticeLocationBundles` (powers the Bundle typeahead)
**Apex in scope:** `PRM_ProgramParticipationTriggerHandler.isParticipatingInCapitatedProgram()`
**Severity:**
- Part 1 (Bug) — **High**: blocks PDM users from updating billing address for any HCF flagged `PRM_ParticipatesInCapitatedProgram__c = true`, even when the HCF is not actually in any Practice Location Bundle
- Part 2 (Search Redesign) — **Medium**: search returns false negatives, no flexible filters, and silently truncates at 500 of 1,582 active bundles
**Type:** Investigation document — implementation deferred (decision required from business owner before fix is built)
**Reproducible record:** `HealthcareFacility` Id `0klUW0000001Nu8YAE` ("Lauren Rosen Wellness LLC", NPI `1487320776`)

---

## 1. Reported Symptom

> "When I try to update the billing address using the PDM Manual Update Practice Location guided flow, it throws an error: *The Practice Location selected is a part of a Capitated Practice Location Bundle, remove Practice Location from the Bundle before proceeding*. When I try to remove it from the bundle, I don't know which bundle the HCF is in. Searching by name isn't helping — the result list is capped at 500 and there's no flexibility on how to search."

The user therefore hits two problems back-to-back:
1. They cannot update the billing address.
2. They cannot find the bundle to remove the PL from (and in this case, no such bundle even exists).

---

## 2. Part 1 — The Validation is Asking the Wrong Question (Bug)

### 2.1 Validation chain (current state)

```
PRM_PDMManualUpdate_English
└─ Step "Update Billing and/or Mailing address"
     ├─ Select  AddressActionType   ("Update Mailing Address" | "Update Billing Address" | "Update Mailing and Billing Address")
     ├─ Formula BundleError         expression: AND(%Facility:IsCapitated% == true, CONTAINS(%AddressActionType%, "Billing"))
     └─ Validation PracticeLocationInActiveBundleError
            show:    BundleError == true
            message: "The Practice Location selected is a part of a Capitated Practice Location Bundle,
                      remove Practice Location from the Bundle before proceeding."
            blocks: Next button (validateExpression = BundleError == false)
```

### 2.2 Where `Facility:IsCapitated` actually comes from

| Layer | Source | Behavior |
|---|---|---|
| OmniScript reads | `%Facility:IsCapitated%` | Set by DataRaptor `PRMDRExtractVendorPracticeLocations` |
| DataRaptor maps | `HealthcareFacility.PRM_ParticipatesInCapitatedProgram__c` → `Facility:IsCapitated` (Boolean) | One-to-one passthrough |
| Field is written by | Apex trigger `PRM_ProgramParticipationTriggerHandler.isParticipatingInCapitatedProgram()` | Sets `true` if at least one **active** `PRM_ProgramParticipation__c` row exists for the HCF (via `PRM_HealthcareFacilityNetwork__r.HealthcareFacilityId`) where `PRM_Program__r.PRM_ProgramType__c = 'CAP'` |

So `Facility:IsCapitated == true` means **"this PL participates in an active CAP program"** — it does **NOT** mean "this PL is a member of an active Practice Location Bundle."

These are two different objects:
- `PRM_ProgramParticipation__c` → linked to `HealthcareFacilityNetwork` (the contract row)
- `PRM_HealthcareFacilityBundle__c` ↔ `PRM_HealthcareFacilityAssociation__c` / `PRM_HealthcareFacilityBundleAssociation__c` → the bundle membership tables

The validation message tells the user to "remove Practice Location from the Bundle" but the formula it's gated on has nothing to do with bundles.

### 2.3 Live data for the reported HCF (`0klUW0000001Nu8YAE`)

Pulled via `sf data query` from `qa-sandbox`:

| Object | Field | Value |
|---|---|---|
| `HealthcareFacility` | Id | `0klUW0000001Nu8YAE` |
| | Name | `Lauren Rosen Wellness LLC(551 W Lancaster Ave Ste 205-0098)` |
| | `PRM_PracticeName__c` | Lauren Rosen Wellness LLC |
| | `PRM_NpiId__r.Npi` | 1487320776 |
| | `AccountId` / `Account.Name` | `001UW00000ejOESYA2` / Lauren Rosen Wellness LLC |
| | `PRM_PracticeClassification__c` | Professional |
| | `PRM_Active__c` | true |
| | `PRM_Primary__c` | true |
| | **`PRM_ParticipatesInCapitatedProgram__c`** | **true**  ← drives `BundleError = true` ← drives the validation block |
| `PRM_HealthcareFacilityAssociation__c` | rows where `PRM_HealthcareFacility__c = 0klUW0000001Nu8YAE` | **0** |
| `PRM_HealthcareFacilityBundleAssociation__c` | rows where `PRM_HealthcareFacility__c = 0klUW0000001Nu8YAE` | **0** |
| `PRM_ProgramParticipation__c` | active CAP rows for this HCF (via HFN) | **1** — `PPA-44783`, Program "Capitation-PRIMARY CARE PHYSICIAN", `PRM_Active__c=true`, `PRM_EffectiveFrom__c=2021-09-01`, `PRM_EffectiveTo__c=null` |

**Conclusion:** The PL is **not in any Practice Location Bundle**. The flag is set because of an active CAP `PRM_ProgramParticipation__c` row. The user therefore cannot satisfy the validation by going through `ManagePracticeLocationBundles` — there is no bundle to remove from.

### 2.4 Diagnosis

Three layered issues:

1. **Wrong concept on the validation gate.** `BundleError` should be derived from actual *Bundle membership*, not from `PRM_ParticipatesInCapitatedProgram__c`.
2. **Misleading error message.** Even if the validation were intentionally tied to CAP-program participation, the wording sends the user down a dead-end path (the bundle UI) for HCFs that have no bundle membership.
3. **Possibly unnecessary entirely.** It's not obvious why a *billing-address-only* update would be functionally blocked just because a PL is in a CAP program — only `Billing` is gated, `Mailing` is unaffected. Business intent needs to be confirmed before we know which fix to ship.

### 2.5 Three candidate fixes (decision required from business owner)

| Option | Validation should become | Effect on `0klUW0000001Nu8YAE` | Notes |
|---|---|---|---|
| **A. The original intent really was Bundle membership (recommended if message wording is to be believed)** | `BundleError = true` only when the HCF has ≥1 active `PRM_HealthcareFacilityBundleAssociation__c` linked to a `PRM_HealthcareFacilityBundle__c` where `PRM_BundleType__c = 'Capitated Bundle'` AND `PRM_Active__c = true` AND `AddressActionType` contains "Billing". Implement by adding a count to the loaded `Facility` JSON (extend `PRMDRExtractVendorPracticeLocations` or a sibling DR), then evaluate `count > 0` in `BundleError`. | **Unblocked** — 0 bundle rows ⇒ validation does not fire | Cleanest data-driven fix; aligns the rule with the message |
| **B. The intent really was CAP program participation** | Keep the existing formula; rewrite the message to: *"This practice location participates in an active Capitated Program (e.g., `PPA-44783`). Billing address changes for capitated PLs must be requested through Provider Contracting / your Case Manager."* Optionally surface the participation `Name` and `Program.Name`. | **Still blocked** — but with honest wording and a clear next step | Lowest-risk metadata change; requires copy from business |
| **C. The validation is unnecessary** | Remove `PracticeLocationInActiveBundleError` from the step entirely. | **Unblocked** | Only do this if Provider Contracting / NetMgmt confirms there is no real downstream impact |

### 2.6 Immediate workaround for the reported HCF

End-date or inactivate `PRM_ProgramParticipation__c` row `PPA-44783`. The trigger will recompute `PRM_ParticipatesInCapitatedProgram__c → false` and the validation will pass. **Do not run this without sign-off from the CAP / Network Management team** — it's a contract-affecting record.

### 2.7 Test cases that must be regressed once a fix is shipped

1. HCF with active CAP program **and** active Capitated Bundle membership → behavior matches new rule (block per Option A; redirect message per Option B; allow per Option C).
2. HCF with active CAP program but **no** bundle membership (the reported case) → currently blocks; under Option A or C must allow billing update.
3. HCF in an active Capitated Bundle but **no** CAP program participation → currently allows; under Option A must block.
4. `AddressActionType = "Update Mailing Address"` → must continue to allow regardless of either flag.
5. `AddressActionType = "Update Mailing and Billing Address"` → must obey the same rule as "Update Billing Address" (the `CONTAINS(...,"Billing")` check already covers this; verify after refactor).

---

## 3. Part 2 — Practice Location Bundle Search Limitations

### 3.1 Current implementation

| Layer | Element | Behavior today |
|---|---|---|
| OmniScript | `PRM_ManagePracticeLocationBundles_English` → step `SelectPracticeLocationBundles` (visible only when `SelectRequestTypeOption ∈ {"Terminate Practice Location Bundle", "Remove from Existing Bundle"}`) | Embeds `PRM_SelectPracticeLocationBundle_English` |
| Embedded OmniScript | `PRM_SelectPracticeLocationBundle_English` → step `SelectBundle` | Hosts a single Type Ahead Block named `PracticeLocationBundle` |
| Type Ahead config | `typeAheadKey: "BundleName"` | Single search field, displays only the Bundle Name |
| DR call | `DRTypeAheadGetPracticeLocationBundles` → DataRaptor `PRMGetPracticeLocationBundles` | Passes typed text in as input parameter `key` |
| DR filter | `Name LIKE '%key%'` on `PRM_HealthcareFacilityBundle__c`, plus `PRM_Active__c = true` | Hard `LIMIT 500` |

### 3.2 Why this hurts users

| Pain point | Evidence |
|---|---|
| **Search uses only `Name`** | Single LIKE filter on `PRM_HealthcareFacilityBundle__c.Name`. Tax ID / NPI / Bundle Identifier do nothing. |
| **Result set silently capped at 500** | Hard `LIMIT 500` in the DR. There are 1,582 active bundles in QA; ~1/3 of the universe can fall off depending on how non-discriminating the input is. |
| **Many similar names in the wild** | E.g. 32 different "Advocare …" bundles share Tax ID `223537011`, all with names beginning "Advocare". Typing "Advocare" returns a long list with no easy disambiguation. |
| **NPI is not searchable at all** | Bundle has no NPI field. NPI lives on the practice locations linked to the bundle. To search by NPI we need to join through `PRM_HealthcareFacilityAssociation__c` → `PRM_HealthcareFacility__c.PRM_NpiId__r.Npi`. Today this path doesn't exist. |
| **No multi-criteria refinement** | Cannot combine "Tax ID 232266054 + effective today + bundle type Capitated" — the typeahead only takes one string. |

### 3.3 QA data profile of `PRM_HealthcareFacilityBundle__c` (Active = true)

| Metric | Value |
|---|---|
| Total active bundles | **1,582** (vs. 1,586 total) |
| `PRM_TaxID__c` populated | 1,574 (99.5%) |
| **`PRM_BundleIdentifierSerial__c` populated** | **1,582 (100%)** — values like `7000003048` |
| `PRM_Account__c` populated | 3 (unusable as a filter) |
| `PRM_BundleType__c = "Capitated Bundle"` | 1,577 (99.7%) |
| `PRM_BundleType__c = "Practice Location Bundle"` | 4 |
| `PRM_BundleType__c = "Inclusive Vendor"` | 1 |
| `PRM_AgreementType__c` populated | 1 of 1,582 (essentially unused) |
| Tax IDs that map to multiple bundles | many — top: 1 Tax ID → 32 bundles; second: 25; third: 21 |
| NPI on Bundle | **does not exist** — must be reached via PL ↔ Bundle association |

### 3.4 Implications for the redesign

- **Bundle Identifier** (`PRM_BundleIdentifierSerial__c`, e.g. `7000003048`) is fully populated and unique per bundle ⇒ best precise lookup key.
- **Tax ID** is populated for 99.5% of bundles but is not unique (a single TIN can map to dozens of bundles for large groups like Advocare). Useful as a pre-filter combined with effective dates / type, not as a sole identifier.
- **Bundle Name** retains value as a "I sort of remember the name" search but should not be the only path.
- **NPI** is the user's natural identifier (regulators, state filings, claim-side conversations all reference NPI). The redesign must support NPI search via a join through `PRM_HealthcareFacilityAssociation__c`.

### 3.5 Proposed redesign — three tiers

#### Tier 1 — "Search by" picker + multi-field DataRaptor (small change, ships fast)

Add a `Select` element `BundleSearchBy` above the typeahead with options:

- **Bundle Name** (default; preserves current behavior)
- **Tax ID**
- **Bundle Identifier** (the `PRM_BundleIdentifierSerial__c`)
- **Practice Location NPI**

Modify (or clone) `PRMGetPracticeLocationBundles` to accept a second input parameter `searchBy` and select the active filter accordingly:

| `searchBy` | Filter | Limit |
|---|---|---|
| `BundleName` | `Name LIKE '%key%'` (existing) | **2000** (covers full active universe + 25% headroom) |
| `TaxID` | `PRM_TaxID__c LIKE '%key%'` | 200 |
| `BundleIdentifier` | `PRM_BundleIdentifierSerial__c = 'key'` (exact) | 50 |
| `NPI` | Join via `PRM_HealthcareFacilityAssociation__c` → `PRM_HealthcareFacility__c.PRM_NpiId__r.Npi = 'key'`, then return distinct related `PRM_HealthcareFacilityBundle__c` records | 100 |

Continue to require `PRM_Active__c = true` on the Bundle.

#### Tier 2 — UX polish on top of Tier 1 (still small)

- **Strip non-numeric input** for Tax ID and NPI before the DR call (users routinely paste `23-1352152` or `23 1352152`). Add a Set Values element that runs `REGEX_REPLACE(BundleSearchKey, "[^0-9]", "")` for those two `searchBy` values.
- **Richer typeahead row label.** Today only `BundleName` is rendered. Switch the template to:
  `BundleName  •  Tax ID  •  Bundle Identifier  •  EffectiveFrom – EffectiveTo  •  Type`
  All four fields are already returned by `PRMGetPracticeLocationBundles` (`HCFBundles:BundleName`, `HCFBundles:BundleTaxId`, `HCFBundles:BundleType`, `HCFBundles:EffectiveFrom`, `HCFBundles:EffectiveTo`). Bundle Identifier needs to be added as an output (single new mapping line).
- **Show count of active associations** in the row label (already returned as `HCFBundles:HCFBundleAssociationsCount`) so the user picks the right active bundle when multiple exist for the same Tax ID.

#### Tier 3 — Replace typeahead with Filter Panel + Result List (best UX, larger build)

For users who don't know which bundle a HCF is in (the "Lauren Rosen" scenario), give them a real search workflow:

1. Replace the `Type Ahead Block` with a step containing:
   - **Filter panel** (all optional, AND-combined): Tax ID, Practice Location NPI, Practice Location Name contains, Bundle Name contains, Bundle Identifier, Effective on date (default `TODAY()`), Bundle Type (multi-select).
   - **Search** button → calls a new Integration Procedure `PRMSearchPracticeLocationBundles`.
   - **Result List Block** with columns: Bundle Name, Bundle Identifier, Tax ID, Bundle Type, Effective From / To, # Active Practice Locations, # Active Capitations. Single-select the row → downstream fields populate exactly as today (`BundleId`, `BundleName`, etc.).
2. Pagination: "Show next 100" button rather than a silent `LIMIT 500`.
3. Tie-in to Part 1: when the user is redirected here from the PDM Manual Update validation (Option A fix), pass the offending `HCF.Id` directly into the search. Returns immediately. If the count is 0 (Lauren Rosen case), show a clear inline message: *"This Practice Location is in 0 active bundles. The validation that sent you here is incorrect — please file a bug ticket / contact your Case Manager."*

### 3.6 Recommendation

Ship **Tier 1 + Tier 2 together**. They unblock 100% of the reported user pain with minimal regression footprint:

- Two new OmniScript elements (`BundleSearchBy` Select, plus an optional Set Values for digit-stripping)
- One DataRaptor edit (`PRMGetPracticeLocationBundles`): add `searchBy` input, switch active LIKE filter, raise limit on Name search, add Bundle Identifier as an output, add NPI join
- Typeahead label template change

Tier 3 becomes a follow-up story when there's appetite for the larger UX redo.

---

## 4. Cross-cutting recommendations

1. **Decision needed from business owner / Provider Contracting** before any code change to Part 1: which interpretation of the existing validation is correct (A, B, or C in §2.5).
2. **Quick win regardless of decision:** rewrite the misleading error message so users blocked today have a clear next step. Even Option B (keep the rule) is acceptable if the message is honest about *why* and *what to do*.
3. **Couple the two fixes.** Once Part 1 lands as Option A, the user landing in `ManagePracticeLocationBundles` will arrive with a known HCF Id; the Tier 3 search makes it easy to confirm "yes, this PL is in N bundles" or "this PL is in 0 bundles, the Part 1 validation is misfiring."

---

## 5. Source-of-truth references

- Validation element: `vlocity_export/OmniScript/PRM_PDMManualUpdate_English/PRM_PDMManualUpdate_English_Element_PracticeLocationInActiveBundleError.json`
- Gating formula: `vlocity_export/OmniScript/PRM_PDMManualUpdate_English/PRM_PDMManualUpdate_English_Element_BundleError.json`
- Action picker: `vlocity_export/OmniScript/PRM_PDMManualUpdate_English/PRM_PDMManualUpdate_English_Element_AddressActionType.json`
- DR that defines `Facility:IsCapitated`: `force-app/main/default/omniDataTransforms/PRMDRExtractVendorPracticeLocations_1.rpt-meta.xml`
- Apex that writes `PRM_ParticipatesInCapitatedProgram__c`: `force-app/main/default/classes/PRM_ProgramParticipationTriggerHandler.cls`
- Bundle typeahead: `vlocity_export/OmniScript/PRM_SelectPracticeLocationBundle_English/PRM_SelectPracticeLocationBundle_English_Element_PracticeLocationBundle.json`
- DR call from typeahead: `vlocity_export/OmniScript/PRM_SelectPracticeLocationBundle_English/PRM_SelectPracticeLocationBundle_English_Element_DRTypeAheadGetPracticeLocationBundles.json`
- Bundle search DR (filters + outputs): `vlocity_export/DataRaptor/PRMGetPracticeLocationBundles/PRMGetPracticeLocationBundles_Items.json`

---

## 6. Open questions for stakeholders

1. **Provider Contracting / Network Management:** Was the original intent of `PracticeLocationInActiveBundleError` to block billing edits for *bundle-member* PLs, *CAP-program-participating* PLs, or both? (Drives the Option A vs B vs C decision.)
2. **Provider Data Management ops:** For HCFs that legitimately participate in CAP but have no bundle (whether by data error or by design), what is the *correct* path to update billing address? Knowing this lets us write a useful error message under Option B.
3. **UX:** Is there appetite for the Tier 3 filter-panel-plus-list redesign in this release, or do we ship Tier 1 + 2 now and queue Tier 3?
4. **NPI search:** Should the NPI search return all bundles whose member PLs match the NPI (recommended), or only the bundle of the *active* membership as of today? This affects join cardinality and the cap.
