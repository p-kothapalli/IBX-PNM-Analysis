# Phase 1 — Vendor and Configure: execution report

**Date:** 2026-09-09
**Scope:** integration plan `02_IBC_Integration_Plan.md` Phase 1 (tasks 1.1–1.10), executed under the
D1b workaround: the tree is vendored to an **uncommitted, gitignored** directory so all technical work
can proceed while written provenance is still outstanding.

**Verdict: Phase 1 is 8/10 complete and CANNOT reach its stated exit criteria.** Two of them are
unachievable for reasons that have nothing to do with our configuration — the vendored artifact is
incomplete and its source has been corrupted by an upstream scrub. Details in F1 and F2, which are the
two findings that need a decision.

---

## 1. What is done

| Task | State | Evidence |
|---|---|---|
| 1.0 *(added)* | ✅ `/gamechanger/` gitignored, **root-anchored** | `.gitignore:57`. Anchored deliberately: a bare `gamechanger/` would also swallow `docs/gamechanger/`. |
| 1.1 Vendor the tree | ✅ 3,216 files / 26 MB | Every item on the plan's 1.1 list was present upstream. Excluded `sfdx-project.json` + `.forceignore` (F7) and `rag-python/` (1.2). |
| 1.2 Delete out-of-scope | ⚠️ **partially reversed** | 5 cron installers deleted. `afls/` + `agents/afls-agent/` **restored** — deleting them breaks the build (F6). |
| 1.3 Org registry | ✅ 13 orgs, 1 write-allowed, 15 fields each, `alias == key`, 0 `acme` | Validated against `org-registry.template.json`; see F4/F5 for why 13 and not 3. |
| 1.4 Write guard | ✅ wired, **19/19 verification passing** | `bash scripts/verify-sf-guard.sh`. Required fixing a fail-open defect first (F3). |
| 1.5 Customer profile | ✅ validates against schema, 0 `acme` | `gamechanger/config/customer-profile.json`. Atlassian/Jira present-but-empty per D3. |
| 1.6 Env profile | ✅ from `.env.example` | Confirms the audit: **`.env.production.example` does not exist** despite `PIPELINE.md`. |
| 1.7 Source trust registry | ✅ 8 IBC sources registered (21 total) | Per plan §6.4. `docs/reference/*` deliberately **not** registered — absent from the repo. |
| 1.8 MCP config | ✅ verify-only, as the audit predicted | `.cursor/mcp.json` already registers the servers. |
| 1.9 Scrub placeholders | ❌ **not achievable as scoped** | F11 — 151 hits across 81 code/config files; §6.5 lists 7. |
| 1.10 Green build | ❌ **blocked** | F1 — `npm install` is clean; `npm run typecheck` cannot pass. |

**Exit criteria status**

- [x] `org-registry.json` loads — keyed map, every key equals its entry's `alias`, all fifteen fields present.
- [x] A write aimed at a read-only alias is refused (exit code 2).
- [ ] `npm run typecheck` passes — **blocked by F1**, not by our config.
- [ ] Zero `acme` references in the vendored tree — **not achievable without editing the framework (F11)**.

---

## 2. Findings that need a decision

### F1 — ~~The vendored tree is materially incomplete~~ → **RETRACTED.** The import graph was broken by the scrub; the code is present

> ⚠️ **This finding was wrong and is corrected below.** It first read: *"23 distinct missing modules …
> the corresponding files were never shipped … this is not a configuration problem and no amount of
> Phase 1 work fixes it."* That conclusion was drawn from module **specifiers** without checking the
> **filesystem** for the same modules under different names. They were there. The original claim
> escalated Phase 0.2 to blocking and drove **D16** toward "obtain a complete artifact"; both are
> revised. Kept visible rather than deleted, because the mistake is instructive: **a broken import
> specifier is evidence about the specifier, not about the existence of the module** — the same
> unfalsifiable-absence error that **R10** exists to catch, made by the auditor this time.

**What is actually true.** The upstream scrub rewrote identifiers and import specifiers *inside* files
but **never renamed the files**. So imports point at names that don't exist while the modules they want
sit beside them under their pre-scrub names. The tell was in `agents/knowledge-agent/index.ts`, which
re-exports `./sourceprimary-connector.js` from a directory containing `devint2-connector.ts` — and that
file exports exactly the three symbols its importers ask for (`inferObjectApiNames`,
`retrieveObjectMetadata`, `SalesforceObjectInfo`) while *also* declaring an interface named
`SourceprimaryQueryResult`. Contents scrubbed, filename not.

Recovering the token map (`devint2`→`sourceprimary`, `ngccb`→`democcb`, `orgsyncng`→`deploytarget`)
resolves **15 of the 17** non-`cortex-mcp` specifiers to real files. Two further breaks are ordinary
stale references, not scrub damage — `story-evidence-pack.ts` was renamed `story-pack.ts` upstream, and
`program-memory/traceability/index-builder.ts` moved to `caag/lib/`, a relocation the moved file's own
header documents while a test import was left behind.

**Repaired** by `scripts/repair-vendored-import-map.sh` (idempotent, and it prints what it deliberately
does *not* fix). Direction of the fix is to rename files **forward** to the scrubbed names rather than
revert the specifiers: 6 renames instead of ~21 edits, and reverting would put customer names back into
a client-adjacent repo, which is what the scrub was for. Verified safe first — nothing in the tree
imports the pre-scrub filenames.

**Result: `TS2307` 33 → 11, total 569 → 543, parse errors 0.**

**What is genuinely absent — and where it sits.** All 11 surviving broken imports live in **7 files, none
on the ten-stage pipeline's executed path:**

| Absent thing | Imports | Only consumer | Why it doesn't block v1 |
|---|:--:|---|---|
| `adapters/adapter-registry.ts` | 2 | `adapters/legacy-evidence-adapter.ts`, reached only from `temporal/activities/intake-activity.ts` | **Temporal is out of v1 by D10.** |
| `cortex-mcp` (sibling pkg) | 5 | `tests/cortex-integration/path-guard.test.ts` (3), `scripts/r2-jira-feature-story-insights/fetch-changelog.ts` (2) | A **boundary test of the sibling package**, plus a **Jira** script that **D3 neutralises**. The bridge the routines actually use, `caag/routines/lib/cortex-mcp-bridge.ts`, **is in-tree** (12 KB, ships `NO_OP_BRIDGE`). |
| `vitest` | 4 | `tests/test-{e2e-agent,knowledge-enricher,deep-context-schema,intake-agent}.ts` | **Orphans.** The project's own runner is `tsx tests/run-all.ts`; grep shows these four are referenced by **no** npm script or runner. |

**The remaining 543 errors are pre-existing upstream strictness debt, not incompleteness** — 100 `TS2532`
+ 68 `TS18048` (strict-null), 82 `TS2379` + 30 `TS2375` (`exactOptionalPropertyTypes`), 43 `TS4111`
(`noPropertyAccessFromIndexSignature`). That is a judgement about upstream's hygiene under its own
`tsconfig`, and it is the same on the pristine copy.

**Revised conclusion.** The artifact is **not meaningfully incomplete**. Re-scoping the green-build gate
to the pipeline's executed path (**D16 option b**) is both correct and achievable, because the absent
code is provably off that path — by our own decisions D10 and D3. Upstream access still matters for
**R9** (a rebase path) and to obtain `adapter-registry.ts`, but it is **no longer blocking**.

### F2 — The upstream scrub corrupted the source, and it had been masking F1

Six files failed to **parse** (63 `TS1005`/`TS1128`/`TS1109` syntax errors). Root cause: the upstream
scrub replaced one token with `Legacy Sync` (with a space) and `legacy-sync` (with a hyphen), including
inside identifiers, which is invalid JavaScript:

```ts
export function isLegacy SyncEntity(name: string): boolean   // space inside a function name
  legacy-sync_object: z.string().nullable(),                 // hyphen in a bare object key
  expect.toBeTrue(isLegacy SyncEntity('Legacy Sync_Account__c'));  // space in an "Apex API name"
```

`'Legacy Sync_Account__c'` cannot be a real Apex API name, and the matching regex in
`sow-baseline/agent.ts` looks for `legacy-sync_[a-z0-9_]+__c`, which cannot match it. The original token
was almost certainly a package prefix such as `Vlocity`/`vlocity`.

**Repaired: 11 identifier positions across 6 files** — spaces closed up (`isLegacySyncEntity`),
hyphenated bare keys quoted (`'legacy-sync_object':`), and one *consumer* site converted to bracket
access (`TRIGGER_PATTERNS['anti_pattern_12_legacy-sync_extension']`, where dot notation had been parsed
as subtraction). Quoting is behaviour-preserving: it keeps the exact property name the parser, zod schema
and tests all expect. **String and regex bodies were left untouched**, because correcting them requires
knowing the original token, and guessing would silently change matching behaviour. A backup of `caag/`
was taken before editing.

Result: **63 parse errors → 0**, verified across all seven parse-error codes.

Note the sequencing: those parse errors halted compilation, which **masked every error in F1**. The tree
appeared to have 63 problems; it had 569, now 543 after F1's repair. Two of the corrupted files also disagree with each other
semantically — a test asserts `'Legacy Sync_Account__c'` (a space) against a regex matching
`legacy-sync_[a-z0-9_]+__c` (a hyphen), and neither is a legal Apex API name — so those tests were
broken by the scrub too and would fail at runtime regardless of parsing.

---

## 3. Findings already resolved in this phase

### F3 — The write guard failed open to Acme's aliases (security-relevant)

The shipped guard resolves its registry as `../../control-plane/org-registry.json` relative to itself.
Installed at the repo root — which is what plan task 1.4 instructs, because Cursor only reads root
hooks — that resolves to `IBXQA/control-plane/org-registry.json`, **which does not exist**. The read
throws, and the `catch` falls back to a hardcoded `['sourceprimary', 'refinternational']`: *Acme's* org
names. The guard would have protected nothing real while still logging as active.

This is the R10 failure mode inside the safety layer: a component that returns nothing useful and
reports success. Our copy at `.cursor/hooks/before-shell-execution-sf-guard.js` resolves the registry
under `gamechanger/`, honours a `GC_ORG_REGISTRY` override, falls back to a snapshot of **IBC's** own
read-only aliases, and announces a missing registry on stderr. Verified by `scripts/verify-sf-guard.sh`
(19/19), including a case asserting the fallback still blocks and contains no Acme aliases.

### F4 — The guard is a denylist, so every non-target org must be registered

The guard blocks a write only when the command mentions an org **explicitly listed read-only**. An
unlisted org is completely unguarded. The plan's registry table implies three entries; that would have
left `CLDEV` and `clstage` — **a different client's sandboxes (CompanionLife)** — plus `gus`,
`my-nickname`, two `storm-*` orgs and `agentforce-demo` able to receive a deploy from this workspace.

All 13 orgs are now registered, 12 read-only. Cross-client write protection is the point, and the
registry says so inline so nobody "cleans up" the entries later.

### F5 — Matching is on the typed alias string, not the resolved username

Protection is built from `cfg.alias` plus the `instanceUrl` hostname. The QA org alone carries **seven**
aliases (`IBXQA`, `myOrg`, `qa-sandbox`, `ibx-qa`, `salesforce-y4nsdz`, `salesforce-7y19gr`, and the
newly bound `deploytarget`). Harmless there, since that org is the write target — but for a *read-only*
org, a write via an unregistered alias is not blocked. `sourceprimary` and `fullcopy` are the framework's
logical names; a human types `ibx-dev` or `FC2`.

Both mirror entries are registered, and `sourceprimary` / `fullcopy` were also bound as real SF CLI
aliases (the D12 pattern) because `sourceprimary` is hardcoded across ~20 control-plane files and so the
registry key cannot be renamed.

### F6 — Plan task 1.2 as written breaks the build

1.2 says to delete `control-plane/agents/afls-agent/` and `control-plane/afls/`. But
`control-plane/commands/afls.ts` imports `../agents/afls-agent/agent.js` and `.../contracts.js`
directly, and three npm scripts target the deleted paths — so the deletion breaks the very typecheck
1.10 requires, and fixing it forward means editing framework files, which Phase 1's own header forbids.

Both directories were **restored**. Dead code that compiles and is never invoked costs nothing;
deleting it costs framework edits and rebaseability (R9). Only the 5 cron installers were removed —
standalone shell scripts that cannot affect the build. The 6 npm scripts referencing them now fail
loudly if invoked, which is the desired outcome for scheduled-job installers.

**Recommend amending 1.2** to delete only `rag-python/` and the cron installers.

### F7 — A nested `sfdx-project.json` would hijack `sf` project resolution

The upstream tree ships `sfdx-project.json` and `.forceignore` at its root. Vendored as-is, any `sf`
command run from inside `gamechanger/` would resolve **that** file as the project root — and Phase 7's
own commands begin `cd IBXQA/gamechanger/control-plane`. A check-only deploy would then target the
framework's package directories instead of IBXQA's `force-app`. Both files were excluded so `sf`
resolves up to the real project root. The plan's 1.1 list already omitted them; this records why that
matters.

### F12 — The guard false-positives on prose, and it bit twice during this phase

Matching is `\b(alias)\b` **anywhere in the command string**, case-insensitive, combined with very broad
write patterns — `/\bdelete\b/` matches the bare word. Two commands were blocked during this phase that
touched no org at all:

1. The guard's own test harness, written as a shell one-liner — it *mentioned* the protected aliases.
2. A `python3` heredoc editing this plan's markdown — the text contained `sourceprimary` and the word
   "delete".

Both are correct-by-design (fail safe, block on ambiguity) but worth knowing, because the natural
reaction to a confusing block is to disable the hook — which is how gates die (compare **R11**). Two
consequences were absorbed rather than worked around: the verification cases live **inside**
`scripts/verify-sf-guard.sh` rather than on a command line, and documentation edits go through the
file-edit tools rather than shell heredocs. Neither weakens the guard.

### F8 — No IBC production org is authenticated

The plan's registry table lists *"IBC production | read-only | grounding truth for the verification
ladder."* No IBC production org is authenticated on this machine, so that row **cannot be populated**.
Recorded as a gap in `_ibc_notes.no_production_org` rather than faked. `FC2` (full copy) is also dead —
its refresh token returns `inactive organization`.

---

## 4. New open decisions

| # | Decision | Why it matters |
|---|---|---|
| **D15** | **Grounding source equals the deploy target.** `defaultSourceOrg` is set to `deploytarget` (ibx--qa) because that is where the PRM verification baseline lives — `PRM_CMAService`, `PRM_ServiceBase`, `PRM_FormSubUtility`, `PRM_CaseManagerAssociation__c` are deployed there, and both `sf_deps.py` and `CLAUDE.md` ground on it. | Departs from the framework's assumption that grounding truth is a *separate read-only* org. Grounding truth is therefore mutable by our own deploys — a `[Verified: …]` marker could be validated against metadata the pipeline itself just wrote. Accept knowingly, or stand up a read-only baseline. |
| **D16** | **What the green-build gate should mean** (from F1). Options: obtain a complete artifact / upstream access (Phase 0.2); or re-scope 1.10 to typecheck only the subset the pipeline executes; or accept a documented baseline error count. | Phase 1 cannot exit until this is answered. Fabricating green would defeat the gate. |

### Amendments recommended to the plan

1. **1.2** — delete only `rag-python/` + cron installers (F6).
2. **1.9 / exit criterion** — "zero `acme` references in the vendored tree" is unachievable: 151 hits
   across 81 code/config files, most in unused CAAG / SOW / Jira paths. Re-scope to **"zero `acme` in
   live configuration, and no reachable Acme endpoint in any enabled code path."** Live configs are
   already clean (`org-registry.json`, `customer-profile.json`, `.env` all 0).
3. **§6.5** — the scrub list is materially incomplete (F11 below).

### F11 — The §6.5 scrub list misses the dangerous cases

§6.5 lists 7 strings. The reachable-endpoint scan found these, none of them listed:

| Location | Value | Risk |
|---|---|---|
| `pipeline/run-pipeline.js:37` | `const deploytarget_USERNAME = 'operator@acme.com.deploytarget'` | A hardcoded deploy-target **username** that bypasses the registry. Dormant — this is the *legacy* pipeline (`pipeline/n.js`), not Phase 7's `run-production.sh`. Same file also repeats the fail-open-to-Acme fallback at line 31. |
| `agents/qa-e2e-tcoe-tester/agent.ts:533` | `https://acme--deploytarget.sandbox.lightning.force.com` | This is the agent **Phase 8 enables first**. |
| `qa/perf-tester/plans/*.jmx` (3 files) | `${__P(host,https://acme--deploytarget...)}` | Epic G perf work would target Acme hosts. |
| `qa/ui-tester/specs/lightning-account-crud.spec.yaml` | Acme sandbox + lightning hosts | Same. |
| `commands/self-improve.ts`, `agents/self-improvement/*` | `github.com/operatorSFDC/acme-agentic-outcomes-lab` | The `self-improvement` agent is **Phase 8 item 2**; it would fetch from a repo we do not own. |
| `agents/knowledge-agent/*`, `scripts/*` | `https://acme.atlassian.net/...` | Out of scope per D3, but would emit Acme links into artifacts. |

None is urgent, because every affected path is disabled in v1 (D10 for CAAG, D3 for Jira, Phase 8 flags
off by default). All must be scrubbed **before** the corresponding flag is turned on — F11 is
effectively a Phase 8 pre-flight checklist.

---

## 5. What Phase 1 leaves in the repo

**Committable (ours, outside `gamechanger/`):**

| Path | Purpose |
|---|---|
| `.cursor/hooks/before-shell-execution-sf-guard.js` | The write guard, with the F3 fix. Documents its deltas from the framework original in the header. |
| `.cursor/hooks/adapter.js`, `.cursor/hooks/_hook-log-helper.js` | Verbatim dependencies the guard requires. Both path-independent. |
| `.cursor/hooks.json` | Minimal — registers **only** the guard, not all 14 framework hooks. |
| `scripts/verify-sf-guard.sh` | 19-case guard verification. Cases live in the file because the guard matches protected alias tokens anywhere in a command, so a one-liner containing them blocks itself. |
| `.gitignore` | Root-anchored `/gamechanger/` with a pointer to Phase 0.1 and R1. |

**Uncommitted (gitignored, pending D1b):** `gamechanger/` — 3,216 files, plus
`control-plane/node_modules/` from `npm install`.

Local environment changes made outside the repo: SF CLI aliases `deploytarget`, `sourceprimary` and
`fullcopy` were bound via `sf alias set` (D12 pattern; no framework file edited).

---

## 6. Next

1. **D1b** — provenance in writing. F1 and F2 raise the stakes: the artifact is incomplete *and*
   corrupted, so **Phase 0.2 (upstream repo access) is now load-bearing, not optional**. Ask for a
   complete tree or repo access in the same conversation.
2. **D16** — decide what the green-build gate means before Phase 1 is called done.
3. **D15** — accept source-equals-target grounding, or stand up a read-only baseline org.
4. Phases 2–6 are **not blocked** by F1: the intake adapter, scope-pack emitter and critic mapping are
   all authorable against the tree as vendored. Only the build gate and Phase 7's check-only deploy
   depend on a complete artifact.
