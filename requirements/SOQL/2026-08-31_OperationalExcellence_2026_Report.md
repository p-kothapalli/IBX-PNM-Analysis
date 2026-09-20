# Operational Excellence Report — CY2026 (Case Managers + Admin Batches)

**Date:** 2026-08-31
**Context:** Business ask for a full-year 2026 operational excellence report: (a) how many Case Managers
(`IndividualApplication`) were completed, broken down by every request type the PDM and Credentialing teams
handle (PAR Form, Off-Cycle, Re-Cred, Ancillary Assessment, PDM Manual Change, PNC, Non-Par, etc.), and
(b) how many admin batches ran successfully in 2026, what each batch does, and how many records each created.
No production access is available from the local environment, so this file defines the extraction strategy
and the exact SOQL to run.

**Status (2026-08-31):**

> ## ✅ COMPLETE — all production data received 2026-08-31
>
> **Business-facing deliverable:**
> [`requirements/OperationalExcellence_CY2026_PROD_Report.md`](../OperationalExcellence_CY2026_PROD_Report.md)
> — that is the document to share. This file is the technical archive: queries, method, provenance and caveats.

| Deliverable | Source | Result |
|---|---|---|
| Full-year intake by request type + team | **Production** | ✅ **107,686** requests (Cred 36,931 / PDM 70,755) |
| Requests completed (throughput) | **Production**, 8 monthly runs | ✅ **92,006** completed (85%) |
| Case-level work volume | **Production** | ✅ **203,356** cases · 145,922 closed · 41,353 open |
| Human vs automation attribution | **Production** | ✅ 28.5% automated (batch 19,036 + bots 11,540) |
| Batch inventory (67 classes, what each does) | Codebase | ✅ Complete (§Section C) |
| Batch run counts + success | **Production** `CronTrigger` + `AsyncApexJob` | ✅ 20 active jobs / 3 paused · 9,918 runs / 7d · 100% success |
| Platform health / exception volume | **Production** | ✅ 2,131,282 rows, root-caused to one job (§P1/§P2) |
| Dead-letter queue backlog | **Production** | ✅ 2,928 unretried (§P3) |

**Consolidation:** `python3 scripts/opex/consolidate_prod.py <dir-with-csvs>` reproduces every rollup above
from the 19 exported CSVs.

**Runnable extract:** every query in this document is packaged as executable scripts —
see [`scripts/opex/README.md`](../../scripts/opex/README.md).

- `scripts/apex/OpEx_01_Aggregates.apex` — anonymous Apex, one run, writes 11 CSVs to Salesforce Files.
- `scripts/apex/OpEx_02_Completions.apex` — anonymous Apex, one run per month, writes the completions CSV.
- `scripts/opex/run_opex_extract.py` — CLI equivalent for anyone with `sf` access to the org.

**No Apex class deployment is required** (no test class, no release process) because the
completions scan is chunked to one month at a time, keeping each run under the 50,000-row
synchronous query limit. Both routes were tested end-to-end against FC2.

---

## 0. Data sourcing decision — where the numbers come from

Four candidate sources were evaluated. **Use a combination of #1 and #2.**

| # | Source | Covers | Verdict |
|---|--------|--------|---------|
| 1 | **FC2 full-copy sandbox** (`prashanth.kothapalli@ibx.com.pie.fullcopy2`) — already authorized locally | Real prod data **2026-01-01 → 2026-05-22** | **Use now.** Zero prod access needed. Gives ~70,654 of the 2026 Case Managers immediately. |
| 2 | **Prod SOQL via read-only service account** (CLI / Workbench / Developer Console) | Full year incl. **2026-05-23 → 2026-08-31** | **Required to close the gap.** Same queries below, just `-o <prod-alias>`. |
| 3 | **Salesforce Reports + Dashboard in prod** | Full year, refreshable | **Use for the recurring/BAU version.** Only source that can filter field-history `New Value` (SOQL cannot — see §A3). |
| 4 | `AsyncApexJob` for batch run history | ~7 days only | **Not viable for a full-year batch report.** See §B1. |

### FC2 refresh boundary — critical caveat

FC2 was refreshed on approximately **2026-05-22/23**. Daily `IndividualApplication` creation volume drops off a
cliff at that date:

```
2026-05-21  927     2026-05-26    1
2026-05-22  458     2026-05-27    1
                    2026-05-29    8
```

Monthly totals confirm it: Jan 15,989 · Feb 17,412 · Mar 13,338 · Apr 15,053 · May 8,872 · **Jun 143 · Jul 126 · Aug 181**.

**Therefore: every query in this file must be bounded `CreatedDate < 2026-05-23T00:00:00Z` when run against FC2.**
Anything after that date in FC2 is post-refresh sandbox test noise, not business volume. Run the *same* queries
unbounded against prod to get Jun–Aug.

---

## PROD ACTUALS — full-year intake (run against production 2026-08-31)

Query run in prod by the user:

```sql
SELECT RecordType.DeveloperName rt, Category cat, COUNT(Id) c
FROM IndividualApplication
WHERE CreatedDate >= 2026-01-01T00:00:00Z
  AND CreatedDate <  TODAY
GROUP BY RecordType.DeveloperName, Category
ORDER BY RecordType.DeveloperName
```

> ### 107,495 requests created — 2026-01-01 → 2026-08-30 (production)

| Request type | Team (`Category`) | Prod (full year) | FC2 (Jan 1–May 22) | Gap (May 23–Aug 30) |
|---|---|---:|---:|---:|
| PRM_PDMManualChange | Provider Data Management | 59,096 | 39,608 | 19,488 |
| PRM_ReCredentialing | Credentialing | 18,609 | 12,590 | 6,019 |
| PRM_PractitionerParticipationRequest | Credentialing | 14,463 | 8,265 | 6,198 |
| PRM_NonParClaimsRequest | Provider Data Management | 10,274 | 6,920 | 3,354 |
| PRM_OffCycleRequest | Credentialing | 2,051 | 1,392 | 659 |
| PRM_PNC | Credentialing | 1,204 | 640 | 564 |
| PRM_NonParticipationRequest | Provider Data Management | 1,168 | 842 | 326 |
| PRM_AncillaryReAssessment | Credentialing | 427 | 236 | 191 |
| PRM_AncillaryAssessment | Credentialing | 131 | 97 | 34 |
| PRM_ProviderChangeRequest | Provider Data Management | 70 | 63 | 7 |
| PRM_CMSPreclusionTerm | Provider Data Management | 2 | 1 | 1 |
| **TOTAL** | | **107,495** | **70,654** | **36,841** |

**Team split (prod, full year):** Provider Data Management **70,610** (65.7%) · Credentialing **36,885** (34.3%).

### What prod confirms

1. **The two counter-intuitive team assignments are correct.** Prod independently returns
   **PNC → Credentialing** and **CMS Preclusion Term → Provider Data Management**, matching the corrected
   §A1 table. The original name-based guesses (PNC→PDM, CMS Preclusion→Cred) were both wrong.
2. **Every record type resolves to exactly one `Category` in prod** — 11 rows for 11 types, no split rows.
   There is no cross-team ambiguity to reconcile.
3. **`PRM_ProfessionalStaffVerification` has zero 2026 volume in prod**, confirming that the 8 rows seen in
   FC2 were post-refresh sandbox noise. **Only 11 request types carry 2026 volume**, not 12.
4. **FC2 covered 65.7% of full-year intake.** The FC2-derived figures elsewhere in this document are a
   Jan 1–May 22 slice, not the year — they are directionally sound and structurally correct, but every
   absolute number below must be re-run in prod before publication.

### Two notes on the prod query itself

- **`CreatedDate < TODAY` excludes today.** In SOQL, `TODAY` resolves to midnight at the start of the current
  day, so this returns Jan 1 → **Aug 30**, not Aug 31. Use `CreatedDate < TOMORROW` (or an explicit datetime)
  to include the current day.
- **The bounds mix timezones:** `2026-01-01T00:00:00Z` is UTC while `TODAY` is evaluated in the running user's
  timezone (UTC−5). Immaterial at this volume, but use explicit UTC datetimes on both sides for a published figure.

---

## Section P — Platform health (production, CY2026)

> **Why this section is in an operational excellence report.** Throughput tells you how much work the teams
> got through; platform health tells you whether the system underneath them is sound. Two production
> findings below materially affect the credibility of operational monitoring and the integrity of the
> provider-network data, and both are live and worsening as of 2026-08-31.

Sourced from the production exports `OpEx_2026_10_exception_log_by_month.csv` and
`OpEx_2026_11_failed_record_staging.csv` (see §Data provenance for the verification that these are genuine
production extracts).

### P1 — Exception log grew 59× and has never recovered

`PRM_ExceptionLog__c`, production, CY2026:

| Month | Rows | vs. Jan–Feb baseline |
|---|---:|---:|
| Jan | 6,748 | — |
| Feb | 8,395 | — |
| Mar | 112,445 | 14.8× |
| Apr | 390,220 | 51.5× |
| May | 366,320 | 48.4× |
| Jun | 373,560 | 49.3× |
| Jul | 427,073 | 56.4× |
| Aug | 446,521 | **59.0×** |
| **Total** | **2,131,282** | |

Baseline is ~7,572/month (Jan–Feb average). At that rate the year would have produced ~60,600 rows.
**~2.07 million rows — 97.2% of the entire 2026 exception log — are excess.** August is the worst month
on record and the trend is still rising, so this is a live, worsening condition rather than a past incident.

At Salesforce's 2 KB/record accounting this backlog occupies roughly **4.1 GB of data storage**.

### P2 — Root cause: one scheduled job logging a non-error as an Error

Because March is byte-identical between prod and FC2, the March breakdown is prod-accurate and can be
diagnosed locally. A single process accounts for the entire increase:

| Process | Feb | Mar | Aug (FC2, indicative) |
|---|---:|---:|---:|
| `PRM_OrgNPDBProcessorService` | 0 | **86,910** | **332,100** (99.8% of month) |
| `PRMOmiUtils fetchAssistiveAidsLabels()` | 4,172 | 5,101 | 21 |
| `PRM_ValidateCAQH` | 853 | 3,228 | — |
| `PRM_CheckCAQHAccessOnDueAccountsBatch` | 67 | 7,308 | — |

Within `PRM_OrgNPDBProcessorService`'s March rows, **86,821 of 86,910 (99.9%)** carry one message:

```
No adverse action logs found for Case Manager
```

First occurrence: **2026-03-20 22:00:10 UTC**. Daily volume was flat at ~6,090 for a week, stepped to
~10,400 on Mar 28, and reached ~14,400/day by August — it grows as the Case Manager population grows.
Rows land only on even hours (00, 02, 04 … 22).

That cadence identifies the driver: scheduled job **`PRM Org NPDB Processor - Every 2 Hours`**
(`0 0 0/2 * * ? *`, state `WAITING`, 1,130 triggers, last fired 2026-08-31 16:00 UTC).

The mechanism is in the code. `PRM_OrgNPDBProcessorBatch.generateQueryString()` selects up to
`Query_Limit__c` (default 10,000) `IndividualApplication` records with no "already processed" predicate
beyond whatever `PRM_ORG_NPDB_Batch_Setting__mdt.Query_Condition__c` supplies, so **the same Case Managers
are re-scanned on all 12 runs per day**. For each one, the service returns an error string when the record
simply has no adverse action logs:

```203:205:force-app/main/default/classes/PRM_OrgNPDBProcessorService.cls
        if (aalCount == 0) {
            return 'No adverse action logs found for Case Manager';
        }
```

The caller treats any non-null return as a failure and writes an `Error`-severity row:

```61:65:force-app/main/default/classes/PRM_OrgNPDBProcessorService.cls
            for (Id caseManagerId : caseManagerIds) {
                String errorMessage = validateAndProcessCaseManager(caseManagerId, result, caseManagerToAals, caseManagerToFileNames);
                if (errorMessage != null) {
                    errorsToLog.add(createExceptionLogRecord(caseManagerId, errorMessage));
                } else {
```

"No adverse action logs exist for this practitioner" is a normal, expected state, not an exception. Three
things compound: it is classified `Error` rather than skipped or logged at `Info`; the batch re-processes
the same population every two hours; and the population only grows. The genuine signals in the same table —
`Adverse action log … is in Error status` (47 + 16 + 11 + …) and `Not all adverse action logs are processed`
(10) — are buried under noise at a ratio of roughly 1,000:1.

**Remediation:** return `null` (or log at `Info`) for the zero-AAL case, and add a processed-state predicate
to the batch scope so completed Case Managers are not re-scanned. Purge the ~2.07M historical rows separately.

### P3 — Dead-letter queue: 2,928 records, none retried

`PRM_FailedRecordStaging__c`, production:

| Source flow | Target object | Status | Failed records |
|---|---|---|---:|
| `PRM_LinkPLPPLTNBatch` | `HealthcareFacilityNetwork` | Pending | 2,795 |
| `PRM_HFNCascadeBatch` | `HealthcareFacilityNetwork` | Pending | 72 |
| `PRM_NetworkCreationBatch` | `HealthcareFacilityNetwork` | Pending | 60 |
| `PRM_UpdateHCFNetworkBatch` | `HealthcareFacilityNetwork` | Pending | 1 |
| **Total** | | | **2,928** |

Every row is `Pending` — nothing has been retried, resolved, or abandoned, so the DLQ is accumulating with
no drain. All four flows target `HealthcareFacilityNetwork`, and `PRM_LinkPLPPLTNBatch` alone is 95.5% of
the backlog. The same query returned **zero rows** against FC2 for Jan 1–May 23, which places the entire
backlog after the May refresh — a second-half-of-year regression, distinct in timing from P1.

### P4 — Summary for the business readout

| Finding | Scale | Since | Business impact |
|---|---|---|---|
| Bogus `Error` rows from the NPDB processor (P1/P2) | ~2.07M rows, ~4.1 GB | 2026-03-20 | Real failures are invisible at ~1,000:1 noise; storage cost; no usable error monitoring |
| Unretried network-link failures (P3) | 2,928 records | after 2026-05-22 | 2,928 `HealthcareFacilityNetwork` records were never created — silent provider-network data gaps |

Neither is a throughput problem, and neither reduces the completion counts elsewhere in this report. Both
are reliability defects that should be raised with the development team independently of the CY2026 numbers.

---

## Data provenance — confirming the exports are production

Three CSVs were exported from production on 2026-08-31 by `scripts/apex/OpEx_01_Aggregates.apex` and
`OpEx_02_Completions.apex`. Provenance was verified before the data was used, because a full-copy sandbox
and its source org are indistinguishable by content alone for pre-refresh periods.

| Month | Prod | FC2 | Reading |
|---|---:|---:|---|
| Jan | 6,748 | 6,748 | identical — pre-refresh copy |
| Feb | 8,395 | 8,395 | identical — pre-refresh copy |
| Mar | 112,445 | 112,445 | identical — pre-refresh copy |
| Apr | 390,220 | 390,255 | +35 in FC2 (0.009%) — immaterial |
| May | 366,320 | 287,829 | diverged — post-refresh |
| Jun | 373,560 | 324,075 | diverged |
| Jul | 427,073 | 335,422 | diverged |
| Aug | 446,521 | 332,599 | diverged |

The exact match on Jan–Mar with sharp divergence from May onward is the expected signature of a genuine
production extract measured against a sandbox refreshed ~2026-05-22. **Two useful consequences:** the
exports are confirmed production, and FC2's fidelity for the pre-refresh window is independently proven,
which validates the Jan–May analysis used throughout this document.

The same logic explains why the January completions export matches FC2 exactly — for a pre-refresh month
it must.

---

## Prod export status — what arrived, what is pending

### Prod-confirmed January completions

`OpEx_02_Completions.apex` for 2026-01 returned **9,229 requests completed**, matching FC2 exactly (as
expected for a pre-refresh month):

| Request type | Completed | Events | Reopened & recompleted | Stage transitions | Distinct touched |
|---|---:|---:|---:|---:|---:|
| PDM Manual Change | 6,529 | 6,530 | 1 | 6,563 | 6,558 |
| Non-Par Claims | 1,106 | 1,106 | 0 | 1,106 | 1,106 |
| Re-Credentialing | 915 | 915 | 0 | 3,298 | 1,151 |
| PAR Form | 485 | 486 | 1 | 4,453 | 2,905 |
| Non-Participation | 167 | 167 | 0 | 329 | 217 |
| Off-Cycle | 16 | 24 | 8 | 348 | 294 |
| Provider Change Request | 7 | 10 | 3 | 23 | 9 |
| PNC | 3 | 3 | 0 | 546 | 530 |
| Ancillary Assessment | 1 | 1 | 0 | 70 | 43 |
| CMS Preclusion Term | 0 | 0 | 0 | 1 | 1 |
| **Total** | **9,229** | **9,242** | **13** | **16,737** | **12,814** |

Ancillary Re-Assessment recorded no January completions. The PNC anomaly documented in §A9 is visible here:
530 distinct PNC requests moved through 546 stage transitions but only 3 reached `Complete` — PNC closure is
not expressed in `PRM_Stage__c`, so PNC throughput must be measured at the Case level.

### All 19 exports received — nothing outstanding

`OpEx_01_Aggregates.apex` (11 CSVs, one run) and `OpEx_02_Completions.apex` (8 CSVs, one per month) both
completed in production. Every figure in this document below this line is production data unless explicitly
labelled FC2.

**Batch-run answers now available from `_08_cron_jobs` and `_09_async_apex_jobs_last7d`:**

- **20 scheduled jobs active, 3 paused.** Paused: `PRM FutureHCProviderNPIActivateBatch` (**never ran** —
  0 triggers, scheduled Jun 2025), `PRM FutureAddressActivateBatch` (last ran 2025-07-22), and
  `PRM_ReinitiateNPDBReport` (last ran 2026-07-31).
- **9,918 batch executions across 41 classes in the trailing 7 days, 100% `Completed`.** No failures or
  aborts; the only non-Completed rows are two schedulers resting in `Queued`.
- Highest-volume: `PRM_HCPFProcessingBatch` 5,101 · `PRM_HFNProcessingBatch` 2,659 ·
  `PRM_CMACreationBatch` 733 · `PRM_LinkPLPPLTNBatch` 530 · `PRM_PractitionerPNCBatch` 277.
- **`PRM Org NPDB Processor` shows 1,885 triggers** at 12/day = ~157 days of running, which back-dates its
  start to late March — independently corroborating the 2026-03-20 start of the exception explosion in §P2
  from a completely separate object.
- **`TimesTriggered` is cumulative since the job was scheduled, not CY2026.** Combined with `AsyncApexJob`'s
  ~7-day retention, **a full-year per-batch run count is not retrospectively recoverable.** This is the one
  business question that cannot be answered for 2026 and requires a durable batch-execution log going forward.

**Batch-attributed record creation** (from `_07_created_by_user`): automation created **30,576 requests
(28.5%)** — `Venkateswara Gutta` (the batch account) 19,036 = Re-Cred 18,609 + Ancillary Re-Assessment 427,
and four bot accounts 11,540 (Barry 8,316 · Kelly 2,180 · Cuthbert 843 · John 201). **Re-Cred is 100%
batch-created — zero human-created re-creds all year** — and produced 46,373 cases.

---

## HEADLINE — Requests completed in 2026

**Agreed headline metric: requests completed.** A "request" = one Case Manager (`IndividualApplication`).
A request counts as completed when its `PRM_Stage__c` transitions to `Complete` or `Case Complete`.

> ### ✅ 92,006 requests completed — PRODUCTION, 2026-01-01 → 2026-08-31
> (92,085 completion events; 79 were requests completed more than once after being reopened)
> **Against 107,686 received = 85% completion rate.**

Sourced from eight monthly runs of `OpEx_02_Completions.apex` in production. The earlier FC2-derived
figure of 51,602 covered Jan 1–May 22 only and is superseded.

| Request type | Received | Requests completed | Rate | Completion events | Reopened & re-completed |
|---|---:|---:|---:|---:|---:|
| PDM Manual Change | 59,215 | 51,869 | 88% | 51,874 | 5 |
| Re-Credentialing | 18,609 | 18,921 | **102%** | 18,938 | 17 |
| Practitioner Participation Request (PAR) | 14,502 | 9,337 | 64% | 9,341 | 4 |
| Non-Par Claims Request | 10,296 | 10,272 | 100% | 10,273 | 1 |
| Off-Cycle Request | 2,057 | 204 | 10% | 252 | 48 |
| PNC | 1,205 | 17 | 1% | 17 | 0 |
| Non-Participation Request | 1,172 | 1,161 | 99% | 1,161 | 0 |
| Ancillary Re-Assessment | 427 | 134 | 31% | 135 | 1 |
| Ancillary Assessment | 131 | 31 | 24% | 31 | 0 |
| Provider Change Request | 70 | 59 | 84% | 62 | 3 |
| CMS Preclusion Term | 2 | 1 | 50% | 1 | 0 |
| **TOTAL** | **107,686** | **92,006** | **85%** | **92,085** | **79** |

**Re-Credentialing exceeds 100% and that is correct** — it is the clearest possible proof that the
event-based method works. 18,921 re-creds completed in the window against 18,609 received; the surplus is
2025-created work finishing in 2026. A created-and-completed cohort measure would have reported ~6,100 for
Re-Cred, a 3× understatement.

**Monthly trend — the backlog inflected in April:**

| Month | Received | Completed | Net |
|---|---:|---:|---:|
| 2026-01 | 15,989 | 9,229 | −6,760 |
| 2026-02 | 17,412 | 10,534 | −6,878 |
| 2026-03 | 13,338 | 9,996 | −3,342 |
| 2026-04 | 15,053 | 15,038 | −15 |
| 2026-05 | 11,457 | 8,908 | −2,549 |
| 2026-06 | 11,461 | 14,836 | **+3,375** |
| 2026-07 | 12,677 | 12,478 | −199 |
| 2026-08 | 10,299 | 10,987 | **+688** |

Q1 ran a ~17k deficit; from April the teams held break-even and went net-positive in June and August.
June's spike is Re-Cred catch-up (5,997 vs a ~2,000 baseline).

**Four types are not measurable this way** (§A9 has the case-level substitute):

| Type | Header completion | Case closure | Reading |
|---|---:|---:|---|
| Off-Cycle | 204 (10%) | 3,809 / 6,262 (61%) | 1,663 parked at `Network Management QC` = de-facto terminal |
| PNC | 17 (1%) | 1,687 / 3,446 (49%) | 768 at `Network Management QC`, 360 at `Application Review` |
| Ancillary Assessment | 31 (24%) | 195 / 322 (61%) | 75 at `PDA Review and Update` |
| Ancillary Re-Assessment | 134 (31%) | 28 / 427 (7%) | **Real backlog** — 399 stalled at `PSV`, 395 `Pending Application` |

### Why this is the right number (and why it is 31% higher than the intake-cohort figure)

Counting "created in 2026 **and** currently complete" gives 39,460 (§A3). That number is **censored** — it
excludes every request created in 2025 that finished in 2026, and it penalises long-cycle work. Measuring
actual completion *events* corrects it:

| Request type | Intake-cohort (§A3) | True completions | Understated by |
|---|---:|---:|---:|
| Re-Credentialing | 1,808 | 5,647 | **3.1×** |
| Practitioner Participation Request | 1,990 | 5,351 | **2.7×** |
| PDM Manual Change | 27,869 | 32,655 | 1.2× |
| **All types** | **39,460** | **51,602** | **1.31×** |

Re-Cred and PAR are the long-cycle processes, so they are the ones the intake-cohort method distorts most.
**Do not headline the §A3 number** — use §A2/§A3 for *intake/backlog* and this section for *throughput*.

### Method (the query is not enough on its own)

`NewValue` is not filterable in SOQL (§A4), so this is an export-then-filter job:

```sql
SELECT IndividualApplicationId,
       IndividualApplication.RecordType.DeveloperName,
       OldValue, NewValue, CreatedDate
FROM IndividualApplicationHistory
WHERE Field = 'PRM_Stage__c'
  AND CreatedDate >= 2026-01-01T00:00:00Z
  AND CreatedDate <  2026-05-23T00:00:00Z
```

Returns 114,046 rows. Then filter `NewValue IN ('Complete','Case Complete')` and count **distinct**
`IndividualApplicationId` per record type.

```bash
SF_ORG_MAX_QUERY_LIMIT=200000 sf data query -o FC2 -r csv -q "<query above>" > stage_hist_2026.csv
```

Two hard gotchas, both of which silently produce wrong answers:

1. **The foreign key is `IndividualApplicationId`, not `ParentId`.** Standard-object history uses a named FK;
   `ParentId` returns `No such column ... on entity 'IndividualApplicationHistory'`.
2. **The CLI silently truncates at 50,000 records.** Without `SF_ORG_MAX_QUERY_LIMIT` the export returns
   50,000 of 114,046 rows with only a warning on stderr — a 56% undercount that looks like a valid result.
   Always reconcile the row count against a `COUNT(Id)` of the same filter.

### Three request types are excluded — they never reach `Complete`

| Request type | Completions | Why |
|---|---:|---|
| PNC | 8 of 640 created | Terminal stage in practice is **Network Management QC** |
| Professional Staff Verification | 0 | No prod-window rows |
| CMS Preclusion Term | 0 | 1 record, still In Progress |

**PNC needs its own completion definition.** Its real lifecycle is
`Application Review → PDA Review and Update → Network Management QC`, and it stops there — 358 of 640 currently
sit in Network Management QC / In Progress and 243 in Application Review / Submitted. Only 8 ever reached
`Complete`.

This is **not** a rework loop: PNC averages 1.5 stage transitions per request (the lowest churn of any
multi-step type), and only one PNC request in 2026 had more than five transitions. The 916
`PDA Review and Update → Network Management QC` transitions are spread across 951 distinct requests — that is
one normal forward step, not ping-pong.

So PNC's ~1% completion rate is a **definition gap, not a backlog crisis**: its work *is* getting done
(816 of 2,006 PNC cases closed, §A9), but the request header is never stamped `Complete`. Either measure PNC
on Case closure, or treat `Network Management QC` as its terminal stage. Flag this to the process owner before
publishing — quoting "PNC completed 8 requests" without this caveat will be read as a failure that isn't real.

### Stage churn by request type (rework indicator)

Transitions per distinct request, 2026 window — useful as a process-efficiency measure in its own right:

| Request type | Transitions | Distinct requests | Per request |
|---|---:|---:|---:|
| Practitioner Participation Request | 33,968 | 11,626 | 2.9 |
| Provider Change Request | 145 | 71 | 2.0 |
| Re-Credentialing | 33,560 | 17,322 | 1.9 |
| Ancillary Assessment | 231 | 120 | 1.9 |
| Non-Participation Request | 1,679 | 914 | 1.8 |
| Ancillary Re-Assessment | 100 | 58 | 1.7 |
| Off-Cycle Request | 3,264 | 1,929 | 1.7 |
| PNC | 1,401 | 951 | 1.5 |
| PDM Manual Change | 32,795 | 32,736 | 1.0 |
| Non-Par Claims Request | 6,902 | 6,900 | 1.0 |

Note the distinct-request counts here **exceed** the created-in-2026 counts (e.g. PAR 11,626 worked vs 8,265
created) — direct confirmation that a large 2025-created backlog was being worked through 2026.

**Off-Cycle has the worst reopen rate:** 42 of its 174 completion events were re-completions (24%), against
132 distinct requests. Worth a callout.

---

## Section A — Case Manager completion by request type

### A1 — The 12 request types (grounded)

`IndividualApplication` record types, verified against
`force-app/main/default/objects/IndividualApplication/recordTypes/`:

Labels and descriptions below are taken verbatim from the record-type metadata; the owning team is taken
from the actual `Category` values on 2026 data (not assumed).

| Record Type (DeveloperName) | Label (verbatim) | Description (verbatim) | Owning team (from `Category`) |
|---|---|---|---|
| `PRM_PractitionerParticipationRequest` | Practitioner Participation Request | Practitioner Participation Intake Form | Credentialing |
| `PRM_ReCredentialing` | Re-Credentialing | Re-Credentialing Process | Credentialing |
| `PRM_OffCycleRequest` | Off-Cycle Request | Off-Cycle Intake Form | Credentialing |
| `PRM_AncillaryAssessment` | Ancillary Assessment | Ancillary Initial Credentialing Process | Credentialing |
| `PRM_AncillaryReAssessment` | Ancillary Re-Assessment | Ancillary Re-Assessment | Credentialing |
| `PRM_PNC` | PNC | PNC Intake Form | **Credentialing** |
| `PRM_ProfessionalStaffVerification` | Professional Staff Verification | Used for yearly professional staff verification for professional staff | no 2026 prod-window rows |
| `PRM_PDMManualChange` | PDM Manual Change | PDM Manual Change | Provider Data Management |
| `PRM_ProviderChangeRequest` | Provider Change Request | Provider Change Request Form | Provider Data Management |
| `PRM_NonParticipationRequest` | Non-Participation Request | Non-Participation Request Form | Provider Data Management |
| `PRM_NonParClaimsRequest` | Non-Par Claims Request | NonPar_Claims_Request recordType | Provider Data Management |
| `PRM_CMSPreclusionTerm` | CMS Preclusion Term | CMS Preclusion Term Record Type | **Provider Data Management** |

**Note on PNC:** the record type label is literally `PNC` ("PNC Intake Form") — the metadata does not expand
the acronym, so do not print an expansion on the report. `Category` puts PNC under **Credentialing**, not PDM.
`PRM_CMSPreclusionTerm` is likewise **PDM**, not Credentialing. Both are counter-intuitive; they were verified
against data rather than inferred from the name.

Query used to ground the ownership column:

```sql
SELECT RecordType.DeveloperName rt, Category cat, COUNT(Id) c
FROM IndividualApplication
WHERE CreatedDate >= 2026-01-01T00:00:00Z
  AND CreatedDate <  2026-05-23T00:00:00Z
GROUP BY RecordType.DeveloperName, Category
ORDER BY RecordType.DeveloperName
```

Every record type resolved to exactly one `Category` — there is no cross-team ambiguity.

### A2 — Query 1: Master breakdown, record type × status

**Object:** `IndividualApplication`
**Use case:** The backbone table of the report — every request type, every status, counted.

```sql
SELECT RecordType.DeveloperName rt, Status st, COUNT(Id) c
FROM IndividualApplication
WHERE CreatedDate >= 2026-01-01T00:00:00Z
  AND CreatedDate <  2026-05-23T00:00:00Z
GROUP BY RecordType.DeveloperName, Status
ORDER BY RecordType.DeveloperName
```

**Result (FC2, 2026-01-01 → 2026-05-22): 70,654 Case Managers created.**

| Record Type | Total | Terminal* | Open |
|---|---:|---:|---:|
| PRM_PDMManualChange | 39,608 | 22,025 | 17,583 |
| PRM_ReCredentialing | 12,590 | 1,808 | 10,782 |
| PRM_PractitionerParticipationRequest | 8,265 | 3,167 | 5,098 |
| PRM_NonParClaimsRequest | 6,920 | 6,834 | 86 |
| PRM_OffCycleRequest | 1,392 | 93 | 1,299 |
| PRM_NonParticipationRequest | 842 | 725 | 117 |
| PRM_PNC | 640 | 3 | 637 |
| PRM_AncillaryReAssessment | 236 | 5 | 231 |
| PRM_AncillaryAssessment | 97 | 82 | 15 |
| PRM_ProviderChangeRequest | 63 | 41 | 22 |
| PRM_CMSPreclusionTerm | 1 | 0 | 1 |
| **TOTAL** | **70,654** | **34,783** | **35,871** |

\* Terminal = `Status IN ('Complete','Approved','Denied','Withdrew')`.

**Gotcha — status vocabulary is not uniform across record types.** Each record type exposes a different
`Status` value set, so there is no single "completed" value:

- `Complete` — PDM Manual Change, Non-Par Claims, Non-Participation, Off-Cycle, PNC, CMS Preclusion, Ancillary (both)
- `Approved` / `Denied` / `Withdrew` — PAR Form, Provider Change Request, Ancillary Assessment, PSV
- `Approved` — Re-Credentialing (no `Complete` in its Status value set at all)

Do **not** write a report that filters `Status = 'Complete'` globally — it silently drops all of PAR and Re-Cred.

### A3 — Query 2: Completion by Stage (the better truth source)

**Object:** `IndividualApplication`
**Use case:** `PRM_Stage__c` is the uniform lifecycle field and carries `Complete` / `Case Complete` for
every record type. This is the number to headline.

```sql
SELECT RecordType.DeveloperName rt, PRM_Stage__c sg, COUNT(Id) c
FROM IndividualApplication
WHERE CreatedDate >= 2026-01-01T00:00:00Z
  AND CreatedDate <  2026-05-23T00:00:00Z
  AND PRM_Stage__c IN ('Complete','Case Complete')
GROUP BY RecordType.DeveloperName, PRM_Stage__c
ORDER BY COUNT(Id) DESC
```

**Result (FC2): 39,460 stage-complete.**

| Record Type | Stage | Count |
|---|---|---:|
| PRM_PDMManualChange | Complete | 27,869 |
| PRM_NonParClaimsRequest | Complete | 6,895 |
| PRM_PractitionerParticipationRequest | Complete | 1,990 |
| PRM_ReCredentialing | Complete | 1,808 |
| PRM_NonParticipationRequest | Complete | 730 |
| PRM_OffCycleRequest | Complete | 58 |
| PRM_OffCycleRequest | Case Complete | 47 |
| PRM_ProviderChangeRequest | Complete | 46 |
| PRM_AncillaryAssessment | Complete | 7 |
| PRM_PNC | Complete | 5 |
| PRM_AncillaryReAssessment | Complete | 5 |
| **TOTAL** | | **39,460** |

**Gotcha — Stage and Status disagree by 4,677 records** (39,460 stage-complete vs 34,783 status-terminal).
The largest divergence is PDM Manual Change (27,869 stage vs 22,025 status). Pick **`PRM_Stage__c` as the
report's definition of "complete"** and state that definition on the report cover, otherwise the two teams
will produce different numbers from the same data.

### A4 — Query 3: "Completed **in** 2026" (throughput, not intake)

> **This query has been executed — see the HEADLINE section above for the result (51,602 requests completed).**
> This section retains the field-coverage analysis that explains *why* field history is the only viable source.

**Object:** `IndividualApplicationHistory`
**Use case:** A2/A3 count records *created* in 2026. Operational excellence normally wants records
*completed* in 2026 — including ones created in 2025 and closed this year.

**There is no reliable completion-date field.** Coverage tested against the 39,413 `Stage = Complete` records:

| Field | Populated | Coverage |
|---|---:|---:|
| `PRM_Decision_Date__c` | 29,131 | 74% |
| `PRM_ApprovedDate__c` | 791 | 2% |
| `RequirementsCompleteDate` | 0 | 0% |

So the authoritative source is field history — `PRM_Stage__c` has `trackHistory=true`.

```sql
SELECT ParentId, Field, OldValue, NewValue, CreatedDate
FROM IndividualApplicationHistory
WHERE Field = 'PRM_Stage__c'
  AND CreatedDate >= 2026-01-01T00:00:00Z
  AND CreatedDate <  2026-05-23T00:00:00Z
ORDER BY CreatedDate
```

**Gotcha — `NewValue` cannot be filtered in SOQL.** Attempting
`WHERE NewValue = 'Complete'` returns:

```
ERROR at Row:1:Column:87
field 'NewValue' can not be filtered in a query call
```

`NewValue`/`OldValue` are `anyType` on history objects and are select-only. Two workarounds:

1. **Bulk-export the rows above and filter `NewValue = 'Complete'` client-side** (CSV → Excel/pandas).
   This is the CLI path.
2. **Build a Salesforce Report** on the *Individual Applications with Field History* report type —
   the report engine **can** filter on `New Value`. This is the better option for the recurring report,
   and is the main reason to prefer source #3 for BAU.

Same technique gives cycle time: pair the earliest `Application Received` history row with the
`Complete` row per `ParentId`.

### A5 — Query 4: Monthly throughput trend

```sql
SELECT CALENDAR_MONTH(CreatedDate) m, RecordType.DeveloperName rt, COUNT(Id) c
FROM IndividualApplication
WHERE CreatedDate >= 2026-01-01T00:00:00Z
  AND CreatedDate <  2026-05-23T00:00:00Z
GROUP BY CALENDAR_MONTH(CreatedDate), RecordType.DeveloperName
ORDER BY CALENDAR_MONTH(CreatedDate)
```

**Result (all record types, monthly intake):** Jan 15,989 · Feb 17,412 · Mar 13,338 · Apr 15,053 · May 8,872 (partial month, refresh cut).

### A6 — Query 5: Cred vs PDM split

**Use case:** The ask separates "PDM and Cred teams". `Category` on `IndividualApplication` carries
`Credentialing` / `Provider Data Management`.

```sql
SELECT Category cat, RecordType.DeveloperName rt, PRM_Stage__c sg, COUNT(Id) c
FROM IndividualApplication
WHERE CreatedDate >= 2026-01-01T00:00:00Z
  AND CreatedDate <  2026-05-23T00:00:00Z
GROUP BY Category, RecordType.DeveloperName, PRM_Stage__c
ORDER BY Category, RecordType.DeveloperName
```

**Result (FC2, headline split of the 70,654):**

| Category | Case Managers created |
|---|---:|
| Provider Data Management (PDM) | 47,434 |
| Credentialing (Cred) | 23,220 |

### A7 — Query 6: Per-analyst productivity

```sql
SELECT Owner.Name owner, RecordType.DeveloperName rt, COUNT(Id) c
FROM IndividualApplication
WHERE CreatedDate >= 2026-01-01T00:00:00Z
  AND CreatedDate <  2026-05-23T00:00:00Z
  AND PRM_Stage__c IN ('Complete','Case Complete')
GROUP BY Owner.Name, RecordType.DeveloperName
HAVING COUNT(Id) > 25
ORDER BY COUNT(Id) DESC
```

### A8 — Query 7: Human-created vs batch/bot-created

**Use case:** Distinguishes team workload from automation output. Records created by a scheduled batch
inherit the `CreatedById` of the user who scheduled it.

```sql
SELECT RecordType.DeveloperName rt, CreatedBy.Name cb, COUNT(Id) c
FROM IndividualApplication
WHERE CreatedDate >= 2026-01-01T00:00:00Z
  AND CreatedDate <  2026-05-23T00:00:00Z
GROUP BY RecordType.DeveloperName, CreatedBy.Name
HAVING COUNT(Id) > 50
ORDER BY RecordType.DeveloperName
```

**Key result — automation is clearly separable:**

- `PRM_ReCredentialing`: **12,590 of 12,590** created by one automation user → 100% batch-generated.
- `PRM_AncillaryReAssessment`: **236 of 236** by the same automation user → 100% batch-generated
  (the Ancillary re-assessment due-date batch).
- `PRM_PDMManualChange`: mixed. Top human is 7,412; four RPA "Bot" users
  (Barry / Kelly / Cuthbert / John Bot) account for ~5,789 combined.
- `PRM_PractitionerParticipationRequest`: predominantly human (top 5 analysts = 7,211), plus ~595 from Bot users.

This query is what lets the report state "the Recred batch created 12,590 **Case Managers** in 2026".

### A9 — Query 8: Work volume at the Case level (the metric the Case Manager count hides)

**Object:** `Case`
**Use case:** A Case Manager (`IndividualApplication`) is the *request header*. The actual work the PDM and
Cred teams perform is tracked as child `Case` records — one per processing step. Counting only Case Managers
**understates team throughput and badly understates low-volume-but-work-heavy request types such as PNC.**

All Cases share a single record type (`PRM_PRM`). The two differentiators are:

- **`Case.Type`** — the *work queue / processing step* (Network Management QC, PSV, QC Review, …)
- **`Case.PRM_CaseManagerRecordType__c`** — a formula (`PRM_CaseManager__r.RecordType.Name`) giving the
  originating *request type*

**Gotcha — `PRM_CaseManagerRecordType__c` is a formula field and cannot be grouped:**

```
ERROR at Row:1:Column:114
field 'PRM_CaseManagerRecordType__c' can not be grouped in a query call
```

Group by the underlying relationship instead:

```sql
SELECT PRM_CaseManager__r.RecordType.DeveloperName rt, IsClosed cl, COUNT(Id) c
FROM Case
WHERE CreatedDate >= 2026-01-01T00:00:00Z
  AND CreatedDate <  2026-05-23T00:00:00Z
GROUP BY PRM_CaseManager__r.RecordType.DeveloperName, IsClosed
```

**Result (FC2): 109,974 Cases vs 70,654 Case Managers — 72,160 closed (65.6%).**

| Request type | Closed | Open | Total Cases | Case Managers | Cases per CM |
|---|---:|---:|---:|---:|---:|
| PRM_PDMManualChange | 27,921 | 11,803 | 39,724 | 39,608 | 1.0 |
| PRM_PractitionerParticipationRequest | 21,262 | 8,538 | 29,800 | 8,265 | 3.6 |
| PRM_ReCredentialing | 10,774 | 11,660 | 22,434 | 12,590 | 1.8 |
| PRM_NonParClaimsRequest | 6,895 | 25 | 6,920 | 6,920 | 1.0 |
| PRM_OffCycleRequest | 2,601 | 1,828 | 4,429 | 1,392 | 3.2 |
| *(no Case Manager linked)* | 116 | 2,291 | 2,407 | — | — |
| **PRM_PNC** | **816** | **1,190** | **2,006** | **640** | **3.1** |
| PRM_NonParticipationRequest | 1,555 | 121 | 1,676 | 842 | 2.0 |
| PRM_AncillaryReAssessment | 5 | 231 | 236 | 236 | 1.0 |
| PRM_AncillaryAssessment | 117 | 104 | 221 | 97 | 2.3 |
| PRM_ProviderChangeRequest | 97 | 22 | 119 | 63 | 1.9 |
| PRM_CMSPreclusionTerm | 1 | 1 | 2 | 1 | 2.0 |
| **TOTAL** | **72,160** | **37,814** | **109,974** | **70,654** | **1.6** |

**This is the fix for the "PNC looks missing" problem.** At the Case Manager level PNC shows 640 requests with
only 5 stage-complete, which reads like a rounding error. At the Case level PNC is **2,006 work items with 816
closed** — it generates ~3.1 cases per request, the third-highest ratio of any request type. PAR Form is
similar: 8,265 requests but 29,800 cases (3.6×). **Report both levels**, or PAR, Off-Cycle and PNC will all
be understated relative to PDM Manual Change (which is a flat 1.0×).

### A10 — Query 9: Throughput by work queue

```sql
SELECT Type t, COUNT(Id) c
FROM Case
WHERE CreatedDate >= 2026-01-01T00:00:00Z
  AND CreatedDate <  2026-05-23T00:00:00Z
GROUP BY Type
ORDER BY COUNT(Id) DESC
```

**Result (FC2):** Network Management QC 46,614 · PSV 21,570 · QC Review 12,728 · Application Review 9,478 ·
OIG Review 7,762 · PDA Review and Update 6,346 · *None* 2,406 · QM Review 1,392 · Non-Par QC Review 833 ·
**PNC 641** · Committee Review 182 · Recred Updates 21 · PDA Termination 1.

Note `Type = 'PNC'` (641) is the *PNC work-queue step*, which is a different number from the 2,006 cases
belonging to PNC Case Managers in A9. Both are legitimate; label them clearly so they aren't conflated.

PNC step detail by status:

| Status | Closed? | Count |
|---|---|---:|
| Closed | yes | 388 |
| New | no | 191 |
| On Hold | no | 49 |
| In Progress | no | 7 |
| Pending NPDB | no | 3 |
| Returned | no | 3 |

---

## Section B — Admin batch runs

### B1 — Why `AsyncApexJob` will not answer "how many batches ran in 2026"

```sql
SELECT MIN(CreatedDate) mn, MAX(CreatedDate) mx, COUNT(Id) c FROM AsyncApexJob
```

**Result in FC2:** oldest `2026-05-29`, newest `2026-08-31`, total 2,114.

Two independent problems:

1. `AsyncApexJob` is **not copied by a sandbox refresh** — the oldest row post-dates the 2026-05-22 refresh.
2. Salesforce **purges `AsyncApexJob` rows after ~7 days** in any org, prod included.

So there is **no way to reconstruct January–August 2026 batch run history from SOQL**, in prod or sandbox.
Anyone promising a full-year "batch runs succeeded" count from `AsyncApexJob` is wrong. Options to actually
get it:

- **Going forward:** enable Event Monitoring (`ApexExecution` / `AsyncApexJob` event log files; 30-day
  retention standard, 1 year with the Event Monitoring add-on), or add a lightweight custom
  `PRM_BatchRunLog__c` write in each batch's `finish()`.
- **Retrospectively (best available):** infer batch activity from the durable business records and error
  logs the batches wrote — queries B3–B5 below.

### B2 — Query 10: Current batch run status (rolling 7-day window only)

```sql
SELECT ApexClass.Name n, JobType jt, Status s, COUNT(Id) c
FROM AsyncApexJob
WHERE CreatedDate >= LAST_N_DAYS:7
  AND JobType IN ('BatchApex','ScheduledApex')
GROUP BY ApexClass.Name, JobType, Status
ORDER BY ApexClass.Name
```

Add `NumberOfErrors`, `JobItemsProcessed`, `TotalJobItems` for a per-run success ratio:

```sql
SELECT ApexClass.Name, Status, TotalJobItems, JobItemsProcessed, NumberOfErrors,
       CreatedDate, CompletedDate, ExtendedStatus
FROM AsyncApexJob
WHERE CreatedDate >= LAST_N_DAYS:7
  AND JobType = 'BatchApex'
ORDER BY CreatedDate DESC
```

### B3 — Query 11: Scheduled job inventory (what is actually wired up)

```sql
SELECT CronJobDetail.Name, State, CronExpression, TimesTriggered, PreviousFireTime, NextFireTime
FROM CronTrigger
ORDER BY CronJobDetail.Name
```

**Result in FC2 (14 rows; prod will have more — sandbox refresh suspends/drops schedules).**
PRM-relevant entries:

| Scheduled job | Cron | Cadence | Times fired |
|---|---|---|---:|
| PRM Org NPDB Processor - Every 2 Hours | `0 0 0/2 * * ? *` | every 2h | 1,130 |
| PRM_DailyScheduledFlowToCheckIfCaseHasExpiredOrNot-1 | `0 0 0 ? * * *` | daily 00:00 | 455 |
| ProcessFutureDateActivation | `0 1 0 * * ?` | daily 00:01 | 59 |
| ProcessFutureDateTermination | `0 0 22 * * ?` | daily 22:00 | 59 |
| PractitionerPSVDailyBatch | `0 30 2 * * ?` | daily 02:30 | 11 |
| PractitionerPNCDailyBatch | `0 0 2 * * ?` | daily 02:00 | 10 |

`TimesTriggered` is cumulative since the job was scheduled, so **run this in prod** — it is the single
best "how many times did this batch run" number available without Event Monitoring.

### B4 — Query 12: Batch-attributed record creation (the "how many cases did the Recred batch create" number)

```sql
SELECT CALENDAR_MONTH(CreatedDate) m, COUNT(Id) c
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_ReCredentialing'
  AND CreatedDate >= 2026-01-01T00:00:00Z
  AND CreatedDate <  2026-05-23T00:00:00Z
GROUP BY CALENDAR_MONTH(CreatedDate)
ORDER BY CALENDAR_MONTH(CreatedDate)
```

Repeat per automated record type. Combine with A8 to attribute to the automation user.

### B5 — Query 13: Batch failures from the durable exception log

**Object:** `PRM_ExceptionLog__c`
**Use case:** Unlike `AsyncApexJob`, this object **survived the sandbox refresh** and spans
`2025-05-22 → 2026-08-31` with **1,893,285 rows**. It is the only retrospective source of batch
failure evidence for CY2026.

```sql
SELECT CALENDAR_MONTH(CreatedDate) m, COUNT(Id) c
FROM PRM_ExceptionLog__c
WHERE CreatedDate >= 2026-01-01T00:00:00Z
  AND CreatedDate <  2026-05-23T00:00:00Z
GROUP BY CALENDAR_MONTH(CreatedDate)
ORDER BY CALENDAR_MONTH(CreatedDate)
```

Then slice by the class/source field to isolate batch-originated errors (inspect the object's
source/class field name before finalising; it is populated by `PRM_ExceptionLogger`).

**Note:** 1.89M rows over ~15 months is a high error volume and is itself an operational excellence
finding worth calling out in the report.

### B6 — Query 14: Dead-letter / failed record staging

```sql
SELECT PRM_SourceFlow__c src, PRM_TargetObject__c tgt, PRM_Status__c st, COUNT(Id) c
FROM PRM_FailedRecordStaging__c
WHERE CreatedDate >= 2026-01-01T00:00:00Z
  AND CreatedDate <  2026-05-23T00:00:00Z
GROUP BY PRM_SourceFlow__c, PRM_TargetObject__c, PRM_Status__c
ORDER BY COUNT(Id) DESC
```

**Result (FC2): 0 rows** for the Jan–May 2026 window. The query is valid (field names confirmed), the
dead-letter queue is simply empty for that period — so this section of the report reads as a clean result
rather than a data gap.

### B7 — Query 15: Async process tracking

```sql
SELECT MIN(CreatedDate) mn, MAX(CreatedDate) mx, COUNT(Id) c FROM PRM_AsyncProcess__c
```

**Result in FC2:** `2025-06-03` → `2026-08-31`, 1,624 rows. Low volume — this is the roster-sync
framework, not general batch tracking. Useful only for the roster-sync section of the report.

---

## Section C — Batch inventory (67 Batchable classes, grounded)

Extracted from class headers in `force-app/main/default/classes/`. Eight are directly `Schedulable`.
Grouped by business function for the report's "what the batch is and what it does" section.

### C1 — Credentialing / Re-Cred lifecycle

| Batch class | What it does | Sched |
|---|---|:-:|
| `PRM_CheckCAQHAccessOnDueAccountsBatch` | Checks CAQH access on accounts due for recred | ✔ |
| `PRM_ReCheckActiveCAQHValidationBatch` | Re-checks for active CAQH application on Recred records | ✔ |
| `PRM_RecredCAQHDueNotificationBatch` | Emails notification 3 months before recred CAQH due | |
| `PRM_RecredCAQHDueNotifyBatchHandler` | Handler for the CAQH due notification batch | |
| `PRM_RecredSendEmailOnDueAccountsBatch` | Sends email on accounts due for recredentialing | |
| `PRM_RecredDuePractitionersReportBatch` | Exports practitioners due for recred (with taxonomies) to CSV | |
| `PRM_PARReCredCommitteeReviewBatch` | Processes approved/removed/denied Case Managers from PAR/ReCred committee review | |
| `PRM_PARReCredCommitteeReviewDenialBatch` | Denial path of the committee review processing | |
| `PRM_PractitionerPSVBatch` / `...Helper` / `...Scheduler` | Daily Primary Source Verification processing | ✔ |
| `PRM_OrgNPDBProcessorBatch` | Organization NPDB batch processing (every 2 hours) | ✔ |
| `PRM_CreateAdverseActionNpdbBatch` | Creates `PRM_AdverseActionLog__c` from OmniScript input for NPDB | |
| `PRM_LetterRecredBatch` | Creates Re-credentialing Letter records | |
| `PRM_LetterWelcomeBatch` | Creates Welcome Letter records | |

### C2 — Ancillary

| Batch class | What it does | Sched |
|---|---|:-:|
| `PRM_CheckDueOnAncillaryReAssessmentBatch` | Creates Ancillary Re-Assessment Case Managers for due records | ✔ |
| `PRM_NotifyReAssessmentDueDateBatch` | Notifies 4 months prior to Re-Assessment due date | |

### C3 — PDM / Provider data maintenance

| Batch class | What it does | Sched |
|---|---|:-:|
| `PRM_ManualUpdatesCrossRefBatch` / `...Helper` | Cross-Reference processing for PDM Manual Update requests | |
| `PRM_ManualUpdatePracLocTerminationBatch` | Terminates practice location + related data for manual updates | |
| `PRM_CrossRefBatch` / `PRM_CrossRefBatchHelper` | General Cross-Reference record processing | |
| `PRM_AccountCreationCrossRefBatch` | Terminates cross-reference location and related records | |
| `PRM_ProvChangePDAPASBatch` | Provider Change → PDA/PAS processing | |
| `PRM_ProvChangeTerminationBatch` | Provider Change termination processing | |
| `PRM_PASUpdateBatch` | PAS update processing | |
| `PRM_UpdateCaseManagerBatch` | Bulk Case Manager field updates | |
| `PRM_UpdateEffectiveDateBatch` | Updates effective date of PL + related objects for PAR and Off-Cycle | |

### C4 — PNC

| Batch class | What it does | Sched |
|---|---|:-:|
| `PRM_PractitionerPNCDailyBatch` / `...Helper` / `...Scheduler` | Daily PNC processing | ✔ |
| `PRM_PractitionerPNCBatch` / `...Helper` | (Re)calculates and updates the PNC flag on Practitioner Accounts | |
| `PRM_PNCPDABatch` / `...Helper` | Creates/updates Network Data for Practice Location | |
| `PRM_PNCPracTxnyNetworkBatch` / `...Helper` | Creates/updates Network Data for Practitioner | |

### C5 — Terminations

| Batch class | What it does | Sched |
|---|---|:-:|
| `PRM_PractitionerTerminationBatch` / `...Helper` | Terminates practitioner data | |
| `PRM_FullPractitionerTerminationBatch` | Full practitioner termination | |
| `PRM_FullPracTerminationRecredBatch` | Full practitioner termination, Recred path | |
| `PRM_FullPracTermForFacilityBatch` | Full practitioner termination for a facility | |
| `PRM_FullPracTermForFacilityRecredBatch` | Facility termination, Recred path | |
| `PRM_FullPracTermRecredBatchService` | Service layer for the Recred termination batches | |
| `PRM_PractitionerTermForFacilityBatch` | Practitioner termination for facility | |
| `PRM_PractitionerTermInitialCredBatch` | Termination on the Initial Cred path | |
| `PRM_PractitionerTermRelateToVendorBatch` | Termination of vendor-related practitioner records | |
| `PRM_AccountTerminationBatch` / `...Helper` | Account-level termination | |
| `PRM_AccountTerminationInitialCredBatch` | Account termination, Initial Cred path | |
| `PRM_PracticeLocationTerminationBatch` | Terminates practice location + related data | |
| `PRM_RCATLocationTerminationBatch` | RCAT location termination | |
| `PRM_RCATNetworkTerminationBatch` | RCAT network termination | |
| `PRM_RCATTerminationBatchHelper` | Shared RCAT termination helper | |

### C6 — Activation / future-dated processing

| Batch class | What it does | Sched |
|---|---|:-:|
| `PRM_FutureDatedProcessingBatch` / `...Handler` / `...Scheduler` | Processes `FutureDataProcessing` records; updates effective dates and active flags | ✔ |
| `PRM_FutureDatedProcBatchSchActivation` | Scheduler — future-dated activation (daily 00:01) | ✔ |
| `PRM_FutureDatedProcBatchSchTermination` | Scheduler — future-dated termination (daily 22:00) | ✔ |
| `PRM_FutureAddressActivateBatch` | Activates future addresses + bell notification | ✔ |
| `PRM_FutureHCProviderNPIActivateBatch` | Activates future HCP NPI on Practice Location | ✔ |
| `PRM_PractitionerActivationBatch` / `...Helper` | Practitioner activation | |
| `PRM_ReinstateVendorAccountBatch` / `...Helper` | Reinstates vendor accounts with >10 practice locations | |

### C7 — Network / facility

| Batch class | What it does | Sched |
|---|---|:-:|
| `PRM_HcFacilityNetworkAutomationBatch` | Facility network automation | |
| `PRM_HFNProcessingBatch` | Async executor for the 5 deferred HFN rollup methods | |
| `PRM_HFNCascadeBatch` | HFN cascade processing | |
| `PRM_UpdateHCFNetworkBatch` | Updates HealthcareFacilityNetwork records | |
| `PRM_UnlinkPracPPLTNBatch` | Asynchronously queries and updates HealthcareFacilityNetwork | |
| `PRM_AddPracPPLTNBatch` / `PRM_LinkPLPPLTNBatch` | Links practitioner ↔ practice location ↔ taxonomy ↔ network | |
| `PRM_NetworkCreationBatch` | Network record creation | |
| `PRM_HCPFProcessingBatch` | Moves selected `HealthcarePractitionerFacility` records | |
| `PRM_HCFBundleAssociationBatch` | Practice Location bundle association | |
| `PRM_PracticeLocationAutomationBatch` | Practice location automation | |

### C8 — Case Manager Association / rosters / other

| Batch class | What it does | Sched |
|---|---|:-:|
| `PRM_CMACreationBatch` | Case Manager Association creation | |
| `PRM_CMAProviderChangeBatch` | CMA creation on the Provider Change path | |
| `PRM_CaseManagerAssociationBatch` | Case Manager Association processing | |
| `PRM_ParFormCmaBatch` | Bulk-safe CMA creation for PAR-form Case Managers | |
| `PRM_UPHSRosterRecordsSyncBatch` | Automated roster attestation — UPHS | |
| `PRM_UPennRosterRecordsSyncBatch` | Automated roster attestation — UPenn | |
| `PRM_NCPDPBatch` / `PRM_NCPDPBatchInput` | Runs all NCPDP record types in one execution | ✔ |
| `DFX_Level4PrimaryTaxonomyFlagUpdateBatch` | Data-fix: Level 4 primary taxonomy flag update | ✔ |
| `LDVAnalyzerBatch` | Large data volume analyzer | |

---

## Notes / gotchas summary

1. **Bound every FC2 query at `2026-05-23`.** Post-refresh rows are sandbox noise (143/126/181 in Jun/Jul/Aug vs ~15k/month real).
2. **Never filter `Status = 'Complete'` globally** — Re-Cred and PAR have no `Complete` status value.
3. **Use `PRM_Stage__c` as the completion definition** and publish that definition; it disagrees with `Status` by 4,677 records.
4. **`NewValue` is not filterable** on `IndividualApplicationHistory` — export and filter client-side, or use a Report.
5. **No reliable completion-date field** — best is `PRM_Decision_Date__c` at 74% coverage.
6. **`AsyncApexJob` cannot give full-year batch history** (~7-day purge, plus not copied by sandbox refresh). Use `CronTrigger.TimesTriggered` from prod, plus `PRM_ExceptionLog__c` for failures.
7. **CSV output from `sf data query -r csv` mangles aggregate aliases** — returns empty columns. Use `--json` and parse, or `-r human`.
8. `PRM_ExceptionLog__c` holds 1.89M rows since 2025-05-22 — worth flagging as an operational finding in its own right.
9. **Report at two levels: Case Manager (request) *and* Case (work).** 70,654 requests generated 109,974 cases. A Case-Manager-only report understates PAR (3.6 cases/request), Off-Cycle (3.2) and PNC (3.1) against PDM Manual Change (1.0).
10. **Formula fields cannot be grouped in SOQL** — `Case.PRM_CaseManagerRecordType__c` errors out. Group by `PRM_CaseManager__r.RecordType.DeveloperName` instead.
11. **Do not expand the "PNC" acronym on the report** — the record type label is literally `PNC` / "PNC Intake Form"; the metadata offers no expansion.
12. **Two team assignments are counter-intuitive and must not be guessed from the name:** PNC is **Credentialing**, CMS Preclusion Term is **PDM**. Both were verified against `Category` data.
13. `Case.Type` is the **work queue/step**, not the request type. `Type = 'PNC'` (641) ≠ cases belonging to PNC Case Managers (2,006). Do not conflate.
14. **The headline is 51,602 requests completed, not 39,460.** The intake-cohort method censors 2025-created work and understates Re-Cred by 3.1× and PAR by 2.7×.
15. **`sf data query` silently truncates at 50,000 rows** — warning goes to stderr only. Set `SF_ORG_MAX_QUERY_LIMIT` and reconcile against `COUNT(Id)`, or you get a 56% undercount that looks valid.
16. **History FK is `IndividualApplicationId`, not `ParentId`** — `ParentId` errors with "No such column".
17. **PNC, Professional Staff Verification and CMS Preclusion Term never reach `Complete`.** PNC's terminal stage is `Network Management QC`. Do not publish "PNC completed 8" without the definition caveat.
18. **Off-Cycle has a 24% reopen rate** (42 re-completions of 174 events) — the highest of any request type.
19. **`CreatedDate < TODAY` silently drops the current day** — `TODAY` is midnight at the start of today. Use `TOMORROW` or an explicit datetime.
20. **Don't mix `...Z` UTC literals with `TODAY`/`YESTERDAY`** — date literals evaluate in the user's timezone, the UTC literal does not. Use explicit UTC on both bounds for published figures.
21. **Only 11 request types have 2026 volume**, not 12 — `PRM_ProfessionalStaffVerification` is zero in prod.
22. **Prod full-year intake is 107,495** (PDM 70,610 / Cred 36,885). FC2 covered 65.7% of it. Treat every FC2-derived absolute in this doc as a Jan 1–May 22 slice pending a prod re-run.
23. **Verify prod exports are actually from prod before trusting them.** A full-copy sandbox is byte-identical to its source for pre-refresh periods, so matching numbers prove nothing on their own. Compare a *post*-refresh month: identical pre-refresh + divergent post-refresh confirms a genuine prod extract (§Data provenance). Identical on both sides means someone ran it against the sandbox.
24. **Item 8's 1.89M exception rows understated prod.** Prod holds **2,131,282 rows in CY2026 alone**, ~97% of which are a single mis-classified non-error (§P1/§P2). Any "top errors" analysis must exclude `PRM_OrgNPDBProcessorService` or it returns nothing but noise.
25. **A month being byte-identical between prod and FC2 is a diagnostic asset.** Jan–Mar 2026 match exactly, so root-cause analysis on those months can be run locally against FC2 with prod-accurate results — no prod access required. This is how §P2 was diagnosed.
26. **`HAVING COUNT(Id) > 25` in the creator-attribution query silently drops the long tail.** It covers 107,297 of 107,686 requests (99.6%), but Provider Change Request (70) and CMS Preclusion Term (2) vanish entirely and the "69 users" figure is a **floor, not a headcount**. State it as "69+" or drop the HAVING clause if you need true headcount.
27. **`Status` and `PRM_Stage__c` disagree by 9,334 records on PDM Manual Change** (Status=Complete 37,214 vs Stage=Complete 46,548). Stage leads. Any dashboard built on `Status` understates PDM completion by ~18%. Definitively settles Stage as the truth source.
28. **Off-Cycle joins PNC as a type whose terminal stage is `Network Management QC`, not `Complete`.** Earlier drafts flagged only PNC. Off-Cycle parks 1,663 of 2,057 requests there (81%) and reports 10% header completion against 61% case closure. Ancillary Assessment (24%/61%) is a third. Only Ancillary Re-Assessment's low rate is a genuine backlog rather than a tracking gap.
29. **`CronTrigger.TimesTriggered` is cumulative since scheduling, and `AsyncApexJob` retains ~7 days.** Together these mean **full-year per-batch run counts are permanently unrecoverable** for 2026. If the business wants this annually, a durable batch-execution log has to be built now — it cannot be backfilled.
30. **`TimesTriggered` can date an incident.** `PRM Org NPDB Processor` at 1,885 triggers ÷ 12/day = ~157 days back-dates its start to late March, corroborating the 2026-03-20 exception onset from an unrelated object. Useful cross-check when you have no deployment history.
31. **16,083 cases have no parent Case Manager** (16,081 closed) — 7.9% of all case volume. Exclude them from per-type case figures or per-request ratios will be wrong.
32. **One individual is credited with 10,194 PDM Manual Changes** (17% of the type, 2.6× the next-highest human). Almost certainly a shared service or bulk-load account. Verify before using per-analyst figures in any productivity comparison.
33. **Never put a Case count next to Case Manager counts in the same headline row.** The published strip read "107,686 received / 92,006 completed / 85% / 41,353 work steps still open" — the first three are `IndividualApplication`, the fourth is `Case`. Readers infer 41,353 of the 107,686 requests are open. The apples-to-apples request figure is **36,558** (§Q1). Always label the unit.
34. **"85% completion rate" is a pace ratio, not a completion rate.** 92,006 ÷ 107,686 divides completion *events* in the window (which include 2025 arrivals) by *arrivals* in the window — two different populations. The true share of 2026 arrivals completed is **66%** (71,128 ÷ 107,686). Both are valid; publish them with distinct labels or a reader will conflate them.
35. **The open-case backlog is 89.6% never-started, not slow-moving.** Only 639 of 41,353 open cases (1.5%) are `In Progress`. Any "cycle time" or "process efficiency" framing of this backlog is wrong — it is queue intake capacity. Earlier drafts characterised the PSV backlog as "actively worked but externally blocked"; in fact 8,515 of its 11,379 (75%) had never been started.
36. **Bucketed status rollups must reconcile to the total.** A first pass at the §Q2 buckets gave 2,723 / 881 / 697, which did not sum to 41,353 — five low-volume statuses (`Ready For MD Review`, `Denied - Appeal Open`, `Rebuttal`, `Provider Outreach`, `Request for Additional Info`) and the 50 `Complete`-but-open anomalies had been dropped. Correct split: 37,052 / 2,728 / 882 / 639 / 52. Always print the total row.

---

## Query Q1 — cohort position: where the 2026 intake stands now

**Object:** `IndividualApplication`
**Use case:** Answers "of the requests that arrived this year, how many are finished *today*?" — the
apples-to-apples counterpart to the throughput figure. This is the query behind **71,128 complete / 36,558
still open / 66%**. Distinct from the history-based completion count, which measures events in the window
and therefore includes 2025 arrivals (hence 92,006 > 71,128).

```sql
SELECT RecordType.DeveloperName, PRM_Stage__c, COUNT(Id)
FROM IndividualApplication
WHERE CreatedDate >= 2026-01-01T00:00:00Z
  AND CreatedDate <  2026-09-01T00:00:00Z
GROUP BY RecordType.DeveloperName, PRM_Stage__c
ORDER BY RecordType.DeveloperName
```

Then treat `PRM_Stage__c IN ('Complete','Case Complete')` as terminal, client-side.

**Result:** 107,686 received → 71,128 at a terminal stage (66%) → 36,558 open. Concentrated in PDM Manual
Change 12,667, PAR Form 10,145, Re-Credentialing 9,996 (32,808 of 36,558). Non-Par Claims is effectively
clear at 32 open.
**Notes / gotchas:** this is emitted by `OpEx_01_Aggregates.apex` as file `_04_stage_by_type` — no new query
needed if that script has already been run. Do **not** subtract this from the 92,006 throughput figure; the
populations overlap. The bottom four types (PNC 1%, Ancillary Re-Assessment 6%, Off-Cycle 7%, Ancillary
Assessment 18%) are the gotcha-28 recording gap, not real progress.

## Query Q2 — open-case backlog decomposed by blocking condition

**Object:** `Case`
**Use case:** Distinguishes a never-started backlog from a slow-moving one. This is the query behind
**37,052 never started (89.6%)** and the correction to the PSV characterisation.

```sql
SELECT Type, Status, IsClosed, COUNT(Id)
FROM Case
WHERE CreatedDate >= 2026-01-01T00:00:00Z
  AND CreatedDate <  2026-09-01T00:00:00Z
GROUP BY Type, Status, IsClosed
ORDER BY COUNT(Id) DESC
```

Filter `IsClosed = false` client-side, then bucket `Status`.

**Result (41,353 open, reconciled):** never started `New` 37,052 (89.6%) · external wait 2,728 (Pending NPDB
926, NPDB Action Required 824, Returned 569, Pending Application 395, + 14 across four statuses) · on
hold/pended 882 · in progress 639 · anomalous 52. Never-started by queue: Network Management QC 24,175, PSV
8,515, PDA Review and Update 2,019, QC Review 1,610.
**Notes / gotchas:** `Type` is the **work queue**, not the request type (gotcha 13). Scope is the *case's*
own `CreatedDate`, so pre-2026 open cases are excluded — 41,353 is the unfinished remainder of 2026-created
work, **not** the org's total open backlog, which needs the date floor removed. 50 cases are `Complete` with
`IsClosed = false`. Emitted by `OpEx_01_Aggregates.apex` as file `_06_cases_by_queue`.
