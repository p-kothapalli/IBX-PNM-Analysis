# USER STORY 7: Remove Stale Active OmniScript Versions From Source Before the ReCred PDA Release

**Persona:** Provider Data Admin (PDA) Specialist
**Priority:** P1
**OmniScript:** `PRM_RecredQC_English` (v8 **and** v13 both marked active in source), `PRM_ReviewRCAT_English` (v8 **and** v10 both marked active in source)
**Integration Procedures:** N/A
**Relevant Requirements:** `requirements/Recred_PDA_ReviewUpdate_Enablement_Gap_Audit.md` §5 H2; blocks safe deployment of US-1, US-2, US-3, US-4

---

## Story

**As a** Provider Data Admin (PDA) Specialist,
**I want** the re-credentialing guided flows to deploy the version the business is actually using,
**So that** a release intended to fix my removal defects cannot silently roll the re-cred review or the RCAT screen back to an older version and undo months of fixes.

**Why it matters:** Two re-credentialing OmniScripts each have **two versions marked active** in the source repository. The platform allows only one active version per flow, so the deployed result is ambiguous — a deployment can activate the older version and silently regress live behaviour. Every defect fix in this batch (US-1 through US-4) requires deploying new OmniScript versions in exactly this area, so the ambiguity must be cleared **before** those releases, not after.

**Persona note:** the work is performed by a developer or release engineer, but the risk being managed is the PDA and Credentialing teams' — an unnoticed version rollback removes capability they rely on daily.

---

## Scope

| Flow | OmniScript | Versions marked active in source | Expected |
|---|---|---|---|
| Re-cred QC review | `PRM_RecredQC_English` | **v8 and v13** | One |
| RCAT review | `PRM_ReviewRCAT_English` | **v8 and v10** | One |

**In scope:** determining which version is genuinely active in each target org, correcting the source so exactly one version per flow is marked active, and a repeatable check to stop it recurring.

**Out of scope:** any functional change to either OmniScript; the re-cred PDA and QC update flows, which each correctly have a single active version.

---

## Current State (from codebase)

Both pairs share identical flow identity — same type, same sub-type, same language — with `isActive` true on two versions:

| File | Version | Active |
|---|---|---|
| `omniScripts/PRM_RecredQC_English_8.os-meta.xml` | 8.0 | **true** |
| `omniScripts/PRM_RecredQC_English_13.os-meta.xml` | 13.0 | **true** |
| `omniScripts/PRM_ReviewRCAT_English_8.os-meta.xml` | 8.0 | **true** |
| `omniScripts/PRM_ReviewRCAT_English_10.os-meta.xml` | 10.0 | **true** |

By contrast, the two flows central to the PDA lane are clean — `PRM_ReCredUpdate_English` has only v7 active and `PRM_ReCredQCUpdate_English` only v3 — which confirms this is drift on two specific flows rather than a repo-wide convention.

**Not yet verified:** which version each target org actually has active. That check is the first task in this story.

---

## Acceptance Criteria

**AC-1 — The genuinely active version is confirmed per org**

**Given** two versions of a re-credentialing guided flow are marked active in source,
**When** a release engineer checks the target orgs,
**Then** the single version actually active in each org is recorded for both flows,
**And** any difference between orgs is documented before source is changed.

**AC-2 — Source reflects exactly one active version per flow**

**Given** the genuinely active version has been confirmed,
**When** the source is corrected,
**Then** exactly one version of each affected flow is marked active in source,
**And** the version marked active matches what the business is using,
**And** the superseded version is retained in source for history but no longer marked active.

**AC-3 — A deployment does not change which version users see**

**Given** the corrected source is deployed to a test org that mirrors production,
**When** the deployment completes,
**Then** a Credentialing Specialist opening the re-cred QC review sees the same version and behaviour as before the deployment,
**And** a user opening the RCAT review sees the same version and behaviour as before,
**And** no capability present before the deployment is missing afterwards.

**AC-4 — The defect-fix releases deploy predictably on top**

**Given** the source has been corrected,
**When** the new versions from the removal and QC defect fixes are deployed,
**Then** the newly activated versions are the ones that take effect,
**And** no older version becomes active as a side effect.

**AC-5 — Recurrence is detectable**

**Given** a developer commits a change that marks a second version of the same flow active,
**When** the repository is checked,
**Then** the duplicate is reported before release,
**And** the check covers every guided flow in the repository, not only the four versions in this story.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| Target-org verification | Investigation | Query the active version per flow in each target org (by type / sub-type / language) and record the result | Drives AC-1 |
| `PRM_RecredQC_English_8.os-meta.xml` / `_13` | Modified metadata | Set `isActive` false on whichever version is not genuinely active | Drives AC-2 |
| `PRM_ReviewRCAT_English_8.os-meta.xml` / `_10` | Modified metadata | Same correction | Drives AC-2 |
| Repository-wide sweep | Investigation | Check every `omniScripts/*.os-meta.xml` for more than one `isActive` true per type / sub-type / language — the two pairs found may not be the only ones | Drives AC-5 |
| Pre-commit or CI check | New automation | Fail the build when a flow has more than one active version in source | Drives AC-5 |

A repository-wide detection sweep can be run as:

```bash
cd force-app/main/default/omniScripts
for f in *.os-meta.xml; do
  if grep -q "<isActive>true</isActive>" "$f"; then
    key=$(grep -oE "<(type|subType|language)>[^<]*</[a-z]+>" "$f" | tr '\n' '|')
    echo "$key $f"
  fi
done | sort | awk '{print $1}' | uniq -d
```

**Related caution for reviewers:** the `<active>` flag on DataRaptors is **not** a usable signal in this repository — all 1,432 DataRaptor files carry `active=false`. Do not attempt the equivalent cleanup on DataRaptors, and do not treat a DataRaptor as disabled on the basis of that tag.

---

## Definition of done

- [ ] AC-1: the genuinely active version of both flows is confirmed and recorded for every target org
- [ ] AC-2: exactly one version per flow is marked active in source
- [ ] AC-3: a mirror-org deployment is verified to leave both flows' visible behaviour unchanged
- [ ] AC-5: the repository-wide sweep is complete and any additional duplicates found are either fixed or logged as follow-ups
- [ ] A check exists that fails when a flow has more than one active version in source
- [ ] Completed **before** the US-1 / US-2 / US-3 / US-4 OmniScript versions are deployed

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|---|---|---|
| 1 | Which version is actually active in each target org for both flows? | The whole story depends on this; correcting source to the wrong version causes the exact regression this story prevents | Technical / Release |
| 2 | Do the orgs disagree with each other (for example QA on one version, production on another)? | May require per-org handling rather than a single source correction | Release |
| 3 | Why do two versions carry an active flag — a partial retrieve, a merge conflict, or a manual edit? | Determines whether the CI check alone is enough or the retrieve/merge process also needs changing | Technical |
| 4 | Should the superseded versions be deleted from source or retained as inactive history? | Retention aids audit but keeps the repository large | Technical / Release |
| 5 | Are there other component types in the repository with the same duplicate-active drift? | May widen the sweep beyond guided flows | Technical |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|---|---|---|---|
| `PRM_RecredQC_English` | OmniScript | **HIGH** | Live re-cred QC review; a rollback loses recent fixes |
| `PRM_ReviewRCAT_English` | OmniScript | **HIGH** | Live RCAT review screen |
| US-1 / US-2 / US-3 / US-4 deployments | Release | **HIGH** | All deploy new OmniScript versions in this area |
| Deployment process | Process | MEDIUM | Gains a guard against recurrence |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|---|---|---|---|
| Target-org active-version verification | Investigation | **S** | Query per flow per org |
| Source corrections | Metadata edit | **S** | Two files |
| Repository-wide sweep | Investigation | **M** | All guided flows |
| Mirror-org deployment verification | QA / Release | **M** | Prove no behaviour change |
| CI / pre-commit duplicate check | Automation | **M** | |

**Total Estimated Effort:** **M** (roughly half a day, mostly verification) — AI-estimated, validate with team.
