# Decision Brief — Does the "shared billing address" invariant apply to Designated Specialty Bundles?

> ## ✅ RESOLVED — 2026-06-22
>
> **Confirmed rule (from PDM business owner):**
>
> > "A Practice Location is in a capitated bundle if-and-only-if there is a **Practice Location Taxonomy (HFN)** on that PL that is **simultaneously**
> > (a) referenced from a `PRM_HealthcareFacilityBundleAssociation__c` row pointing to an active `PRM_BundleType__c='Capitated Bundle'`, **and**
> > (b) linked to an active `PRM_ProgramParticipation__c` whose `PRM_Program__r.PRM_ProgramType__c='CAP'`."
>
> This is **stricter** than Option A in §5 below (HFBA + active capitated) by adding the per-HFN CAP-program-participation conjunction. It is **not** Option B — Designated Specialty Bundle / Designated Specialty Bundle Network records on `PRM_HealthcareFacilityAssociation__c` (HFA) are explicitly **not** part of this rule.
>
> **Verifying data (QA, 2026-06-22):**
>
> | Case | HCF | HFBA active capitated | CAP PP at the bundled HFN | Conjunction count | Expected | Result |
> |---|---|---|---|---|---|---|
> | Negative control (Lauren Rosen) | `0klUW0000001Nu8YAE` | 0 across 59 HFNs | 1 (on a non-bundled HFN) | **0** | unblock | ✅ |
> | Positive control (LabCorp Holdings) | `0klUW0000001E0SYAU` | 1 (HFN `0bYUW000000XTDD2A4` → "LabCorp of America Bundle") | 1 ("Capitation-LAB FUND" on same HFN) | **1** | block | ✅ |
>
> **Population impact under the confirmed rule (QA, 2026-06-22):**
> - HCFs that satisfy the conjunction org-wide: **1,051**
> - Of today's 9,368 flagged-and-blocked HCFs: **1,010** stay blocked, **8,358 are released** (Lauren-class).
>
> **Implementation status:** the unblocker user story `US_PDM_BillingAddress_CapitatedBundle_ValidationFix.md` is off HOLD; its Technical Section has been rewritten to use the confirmed conjunction.

**Audience:** Provider Contracting · PDM Business Owners · PDM Product · Provider Data Management Engineering Lead
**Raised by:** Engineering, while patching `US_PDM_BillingAddress_CapitatedBundle_ValidationFix.md`
**Status:** RESOLVED 2026-06-22 — see banner above; sections below preserved as historical record
**Decision needed by:** ~before the next PDM Manual Update release~ — answered

---

## 1. The single question we need answered

> When a Practice Location is updating its **billing address** in the PDM Manual Update guided flow, must the system block the change if the PL is linked to an active capitated bundle through:
>
> 1. **Only `PRM_HealthcareFacilityBundleAssociation__c` (HFBA — "Practice Location Bundle Association")** — the "core" bundle membership the existing **Manage Practice Location Bundles** screens already manage, or
>
> 2. **Both HFBA *and* `PRM_HealthcareFacilityAssociation__c` (HFA — "Practice Location Association") rows whose RecordType is `Designated Specialty Bundle` or `Designated Specialty Bundle Network`** — referral / specialty-designation linkages?

The validation logic in the OmniScript today blocks a separate population (everyone with `HealthcareFacility.PRM_ParticipatesInCapitatedProgram__c = true`, set by the CAP-program-participation trigger). That population is neither A nor B and includes Lauren Rosen, who is in B but not A. We need the business intent so we can write the right check.

---

## 2. Why the question exists at all — two parallel "PL-in-Bundle" sObjects

The org has two custom objects that can both express "this Practice Location is in this Bundle":

| sObject | Salesforce label | HCF reference | Bundle reference | Practical use |
|---|---|---|---|---|
| `PRM_HealthcareFacilityBundleAssociation__c` | **Practice Location Bundle Association** | `PRM_PracticeLocationTaxonomy__c` (HFN) → `HealthcareFacilityId` | `PRM_HealthcareFacilityBundle__c` | Created and terminated by **Manage Practice Location Bundles → Add / Remove** flow. Treated as the "core" bundle membership. |
| `PRM_HealthcareFacilityAssociation__c` | **Practice Location Association** | `PRM_PracticeLocationTaxonomy__c` (HFN) → `HealthcareFacilityId` | `PRM_RelatedBundle__c` (only on RecordTypes *Designated Specialty Bundle* and *Designated Specialty Bundle Network*) | Carries a wider mix of provider associations; the bundle-bearing record types appear to encode specialty / referral designations. |

The PDM Manual Update validation today references **neither**; it gates on `HealthcareFacility.PRM_ParticipatesInCapitatedProgram__c`, which is a CAP-program-participation flag written by `PRM_ProgramParticipationTriggerHandler` based on `PRM_ProgramParticipation__c` rows of program type `CAP`. That flag has no direct relationship to bundle membership.

The unblocker story rewrites the validation to use *bundle membership* as the gate instead of the CAP flag. Whether that gate counts only HFBA or also HFA is the open question.

---

## 3. The data — QA, captured 2026-06-21

| Slice | Count | What it tells us |
|---|---|---|
| Active HCFs in QA | 372,148 | baseline |
| HCFs flagged `PRM_ParticipatesInCapitatedProgram__c = true` (today's blocker) | **9,368** | every one is currently blocked from billing-address updates regardless of bundle membership |
| Distinct HCFs with active membership in an active capitated **HFBA** | **1,478** | "core" bundle membership |
| Distinct HCFs with active membership in an active capitated **HFA** (RT *Designated Specialty Bundle* or *Designated Specialty Bundle Network*) | **7,021** | ~5× larger than HFBA |
| Of the 9,368 flagged HCFs: in HFBA path | 1,021 | overlap with the "core" bundle population |
| Of the 9,368 flagged HCFs: in HFA path | **6,866** | overlap with the specialty-bundle population |
| Active capitated bundles total | 131 | all 131 active bundles have `PRM_BundleType__c = 'Capitated Bundle'` |

### HFA RecordType breakdown (which RTs even carry bundles)

| RecordType | Active rows | Carry a bundle? | Plain-English read |
|---|---|---|---|
| `Association` | 455,427 | none | provider ↔ network/account associations |
| `Designated Specialty Site` | 13,182 | none | specialty designation, no bundle |
| `Contract To` | 11,139 | none | contractual reference |
| **`Designated Specialty Bundle`** | 10,289 | **10,075** | provider designated *into* a specialty bundle (referral) |
| `Designated Specialty Site Network` | 4,258 | none | network-level specialty site |
| **`Designated Specialty Bundle Network`** | 356 | **276** | network-level specialty bundle designation |

### Reproducing case — Lauren Rosen Wellness LLC

| Check | Result |
|---|---|
| `HealthcareFacility.Id` | `0klUW0000001Nu8YAE` |
| `PRM_ParticipatesInCapitatedProgram__c` | true (drives today's block) |
| Active capitated **HFBA** rows (via HFN traversal) | **0** |
| Active capitated **HFA** rows | **1** → `a1hUW000001eEfdYAE` (RT *Designated Specialty Bundle*, bundle "LabCorp of America Bundle") |
| Active CAP `PRM_ProgramParticipation__c` rows (via HFN) | 1 (PPA-44783, Capitation-PRIMARY CARE PHYSICIAN) |

Direct CLI query a stakeholder can re-run any time:

```bash
sf data query --target-org qa-sandbox --query "
SELECT Id, RecordType.Name, PRM_RelatedBundle__r.Name
FROM PRM_HealthcareFacilityAssociation__c
WHERE PRM_PracticeLocationTaxonomy__r.HealthcareFacilityId='0klUW0000001Nu8YAE'
  AND PRM_Active__c=true
  AND PRM_RelatedBundle__c!=null
  AND PRM_RelatedBundle__r.PRM_Active__c=true
  AND PRM_RelatedBundle__r.PRM_BundleType__c='Capitated Bundle'"
```

---

## 4. What the existing remove-from-bundle flow can actually do

The **Manage Practice Location Bundles → Remove from Existing Bundle** flow ultimately calls `PRM_OmniUtils.TerminateHCFBundleAssocationsBatch` → `PRM_HCFBundleAssociationBatch`. That batch's source query is:

> `... FROM PRM_HealthcareFacilityBundleAssociation__c WHERE ...`
> (`force-app/main/default/classes/PRM_HCFBundleAssociationBatch.cls`)

**It only operates on HFBA.** It cannot end-date or terminate HFA rows. So if the new validation counts HFA-bound bundle membership, the validation message that says *"use Manage Practice Location Bundles → Remove from Existing Bundle"* will land users on a screen with nothing to act on for ~6,866 HCFs in QA.

This remove-flow gap exists today regardless of which option we pick — but Option B makes it customer-visible to a much larger population.

---

## 5. The three concrete options

### Option A — HFBA-only (recommended)

**Rule:** Block billing-address updates if-and-only-if the PL has at least one active row on `PRM_HealthcareFacilityBundleAssociation__c` joined to an active `'Capitated Bundle'`.

| Pro | Con |
|---|---|
| Matches the existing remove-from-bundle flow's scope (no message-vs-flow mismatch) | Allows billing-address change for ~6,866 HCFs that are HFA-bundled to a capitated bundle (Lauren-class) |
| Aligns with the plain-English semantic of "Practice Location **Bundle** Association" being the bundle-of-record | Requires sign-off that the specialty-designation linkages don't carry the shared-billing constraint |
| Unblocks the reproducing case (Lauren) and similar PLs immediately | If business later decides specialty designations *do* enforce shared billing, we'll need a follow-up story |
| Minimal-surface fix; rollback is a one-line OmniScript version revert | |

**Engineering signal that points to A:** the shared-billing-address invariant is a co-tenancy concept (PLs under one tax ID at the same physical operation share an address). HFA RecordTypes named *Designated Specialty Bundle* read as referral relationships (e.g., "this PCP refers labs to LabCorp"), not co-tenancy. The size of the HFA population (7,021 distinct HCFs across many specialties) is also more consistent with a referral construct than a co-tenancy one.

### Option B — Both HFBA and HFA (RT *Designated Specialty Bundle* / *Designated Specialty Bundle Network*)

**Rule:** Block if either:
1. PL has an active capitated HFBA row (Option A), **or**
2. PL has an active row on HFA with `RecordType.Name IN ('Designated Specialty Bundle', 'Designated Specialty Bundle Network')` AND `PRM_RelatedBundle__r.PRM_Active__c = true` AND `PRM_RelatedBundle__r.PRM_BundleType__c = 'Capitated Bundle'`.

| Pro | Con |
|---|---|
| Preserves blocking for ~6,866 currently-blocked HCFs that the Option-A rule would release | The validation message ("use Manage Practice Location Bundles → Remove from Existing Bundle") is a dead end for the HFA case — the existing remove-flow does not handle HFA |
| Conservative: errs on the side of preserving today's behaviour | The user is left telling Provider Contracting "the screen says remove me from the bundle but there's no remove button"; UX gap |
| Aligns the rule with whatever invariant *is* expressed via specialty designations (if any) | Lauren Rosen-class users still blocked indefinitely; doesn't unblock the business |
| | The validation message would have to branch ("HFBA case → use this screen"; "HFA case → contact Provider Contracting"), which means more wording for stakeholder review |

**This option is only the right answer if** Provider Contracting confirms that specialty-bundle designations *do* enforce a shared billing address.

### Option C — Pause and audit (heaviest, lowest risk)

**Rule:** Don't ship the validation change until Engineering audits whether any HFA-bundled HCFs in production today have a billing-address change history that violates the bundle's other-PLs' billing addresses (i.e., did the existing flag-based block actually prevent real shared-billing violations, or has the system been tolerating them?).

| Pro | Con |
|---|---|
| Highest information; resolves the question with empirical evidence | Lauren-class users blocked for the duration of the audit (likely 1–3 weeks) |
| Helps inform whether shared-billing is enforced anywhere else (LWC layouts, Apex, etc.) for HFA | Engineering effort: extract billing-address change history per HCF, group by bundle, look for divergence |
| Useful even if Option A is later chosen — surfaces broader data-quality issues | |

---

## 6. Recommendation

**Choose Option A**, with three guardrails that keep us safe if the read is wrong:

1. **Add a one-time pre-deploy audit** (run on the day of release): list the distinct HCFs that fall into the "HFA-bundled but not HFBA-bundled" set among the currently-flagged 9,368, group by bundle, and spot-check ten of them with Provider Contracting. If any spot-check rejects "this PL doesn't need to share billing with the bundle's other PLs," halt the release and switch to Option B.
2. **Telemetry on rollout:** add a Platform Event or audit-log row each time the new validation lets a billing-address update through that *would have been blocked under the old rule but had a non-zero HFA capitated-bundle count*. Watch the event volume and rollback if Provider Contracting reports any complaints in the first 14 days.
3. **Open a follow-up story** to either (a) bring HFA into the Manage Practice Location Bundles screens so the remove-flow can handle it, or (b) explicitly document HFA bundle-bearing record types as out-of-scope for shared-billing enforcement. The choice depends on Provider Contracting's answer to the question in §1.

Rationale: the data shape (referral-style HFA, co-tenancy-style HFBA) and the existing remove-flow scope (HFBA-only) both point to A as the intended invariant. The audit + telemetry + follow-up story keep us safe if that intent is wrong.

---

## 7. What we need from this brief's reviewers

Please reply to engineering with:

1. **The chosen option (A, B, or C),** or a different rule we haven't articulated.
2. For Option A: confirmation that specialty-bundle designations (HFA RTs *Designated Specialty Bundle* and *Designated Specialty Bundle Network*) do **not** require all linked PLs to share a billing address.
3. For Option B: the desired wording of the user-facing validation message for the HFA branch (since the existing "Remove from Existing Bundle" path is unavailable for HFA).
4. For Option C: who owns the audit and the target completion date.
5. **Any other invariant in the org that depends on the same answer** (e.g., other validations, reports, NetSuite extracts, etc.) so we can scope a single decision to the entire surface.

---

## 8. Pre-deploy data audit (run as soon as a decision is made)

Once the rule is chosen, Engineering will run this audit in QA and Stage as part of the release readiness check. The output should be reviewed alongside this brief so reviewers see the populations affected by their choice.

```sql
-- A. HCFs flagged today that the new HFBA-only rule would BLOCK (no change in behaviour)
SELECT COUNT_DISTINCT(PRM_PracticeLocationTaxonomy__r.HealthcareFacilityId)
FROM   PRM_HealthcareFacilityBundleAssociation__c
WHERE  PRM_Active__c = true
  AND  PRM_HealthcareFacilityBundle__r.PRM_Active__c = true
  AND  PRM_HealthcareFacilityBundle__r.PRM_BundleType__c = 'Capitated Bundle'
  AND  PRM_PracticeLocationTaxonomy__r.HealthcareFacility.PRM_ParticipatesInCapitatedProgram__c = true

-- B. HCFs flagged today that the new HFBA-only rule would RELEASE (delta vs. today)
SELECT Id, Name, PRM_NpiId__r.Npi
FROM   HealthcareFacility
WHERE  PRM_ParticipatesInCapitatedProgram__c = true
  AND  Id NOT IN (
    SELECT PRM_PracticeLocationTaxonomy__r.HealthcareFacilityId
    FROM   PRM_HealthcareFacilityBundleAssociation__c
    WHERE  PRM_Active__c = true
      AND  PRM_HealthcareFacilityBundle__r.PRM_Active__c = true
      AND  PRM_HealthcareFacilityBundle__r.PRM_BundleType__c = 'Capitated Bundle'
  )

-- C. Of the released set in (B), how many also have HFA capitated-bundle linkage
--    (these are the population that Option A releases but Option B would still block)
SELECT COUNT_DISTINCT(PRM_PracticeLocationTaxonomy__r.HealthcareFacilityId)
FROM   PRM_HealthcareFacilityAssociation__c
WHERE  PRM_Active__c = true
  AND  RecordType.Name IN ('Designated Specialty Bundle', 'Designated Specialty Bundle Network')
  AND  PRM_RelatedBundle__c != null
  AND  PRM_RelatedBundle__r.PRM_Active__c = true
  AND  PRM_RelatedBundle__r.PRM_BundleType__c = 'Capitated Bundle'
  AND  PRM_PracticeLocationTaxonomy__r.HealthcareFacility.PRM_ParticipatesInCapitatedProgram__c = true
  AND  PRM_PracticeLocationTaxonomy__r.HealthcareFacilityId NOT IN (
    SELECT PRM_PracticeLocationTaxonomy__r.HealthcareFacilityId
    FROM   PRM_HealthcareFacilityBundleAssociation__c
    WHERE  PRM_Active__c = true
      AND  PRM_HealthcareFacilityBundle__r.PRM_Active__c = true
      AND  PRM_HealthcareFacilityBundle__r.PRM_BundleType__c = 'Capitated Bundle'
  )
```

Last QA snapshot for these three figures (2026-06-21):
- A: **1,021** flagged HCFs already blocked under the new rule (subset of the 1,478 HFBA-bundled total)
- B: ~7,000–8,000 flagged HCFs released by Option A (precise count to be re-run on release day; equals 9,368 minus A)
- C: ~6,866 of those have an HFA capitated-bundle linkage (the population whose treatment differs between Option A and Option B)

---

## 9. Pointers to source-of-truth artifacts

- User story (currently on hold): [`./US_PDM_BillingAddress_CapitatedBundle_ValidationFix.md`](./US_PDM_BillingAddress_CapitatedBundle_ValidationFix.md)
- Investigation: [`../PDM_BillingAddress_CapitatedBundle_BugFix_And_BundleSearch_Redesign.md`](../PDM_BillingAddress_CapitatedBundle_BugFix_And_BundleSearch_Redesign.md)
- Larger build-ready plan (WS-1 inline panel, WS-2 bundle-search redesign): [`../PDM_BundleAware_BillingAddress_And_BundleSearch_Implementation_Plan.md`](../PDM_BundleAware_BillingAddress_And_BundleSearch_Implementation_Plan.md)
- Apex remove-flow (HFBA-only): `force-app/main/default/classes/PRM_HCFBundleAssociationBatch.cls`
- Capitated-flag trigger handler: `force-app/main/default/classes/PRM_ProgramParticipationTriggerHandler.cls`
- OmniScript validation today: `vlocity_export/OmniScript/PRM_PDMManualUpdate_English/PRM_PDMManualUpdate_English_Element_BundleError.json` and `..._Element_PracticeLocationInActiveBundleError.json`
