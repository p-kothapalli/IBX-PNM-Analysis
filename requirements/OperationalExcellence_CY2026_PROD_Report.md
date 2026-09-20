# Operational Excellence Report — CY2026

**Reporting period:** 1 January 2026 – 31 August 2026 (8 months)
**Source:** IBX Salesforce **production** org, extracted 31 August 2026
**Scope:** Provider Data Management (PDM) and Credentialing request throughput, plus administrative batch operations
**Prepared for:** Business stakeholders — PDM and Credentialing leadership

> **Method note.** A *request* is one Case Manager record (`IndividualApplication`) — the header a specialist
> works. A *case* is one work item within that request; a single request generates between 1 and 4 cases
> depending on type. Both are reported, because request counts alone understate Credentialing's workload by
> roughly half. Full extraction method, queries and data caveats are in
> [`requirements/SOQL/2026-08-31_OperationalExcellence_2026_Report.md`](SOQL/2026-08-31_OperationalExcellence_2026_Report.md).

---

## 1. Executive summary

Two units are reported and must not be conflated. A **request** is one `IndividualApplication` (the "Case
Manager"). A **work item** is one `Case` inside it. Every figure below is labelled with its unit.

| Measure | Unit | Result |
|---|---|---:|
| Received in 2026 | request | **107,686** |
| Completed during 2026 (events in period) | request | **92,006** |
| Of the 2026 arrivals, now at a complete stage | request | **71,128** (66%) |
| Of the 2026 arrivals, still open | request | **36,558** |
| Generated in 2026 | work item | **203,356** |
| Closed | work item | **145,922** (78%) |
| Open at period end | work item | **41,353** |
| — never started (status `New`) | work item | **37,052** (90% of open) |
| Requests created by automation | request | **30,576** (28.5%) |
| Active scheduled jobs | job | **20** (3 paused) |
| Batch executions, 100% success rate | run | **9,918** in the trailing 7 days |

**Three completion figures, three questions.** 92,006 is throughput — what the teams got through, including
requests that arrived in late 2025. 66% (71,128 of 107,686) is the cohort position — how much of *this
year's* intake is finished. The 85% quoted elsewhere is 92,006 ÷ 107,686, a **pace** ratio whose numerator
and denominator are different populations; it is not a completion rate and should not be read as one.

**Five things leadership should take away.**

1. **Throughput is keeping pace with intake.** 92,006 of 107,686 requests completed. The gap is normal
   work-in-progress, not a growing backlog — the last three months completed 38,301 against 34,437 received,
   so the teams are now closing more than arrives.

2. **Credentialing does 61% of the actual work on 34% of the requests.** PDM receives nearly twice
   Credentialing's request volume (70,755 vs 36,931) but Credentialing generates 114,993 work items against
   PDM's 72,280. PAR Form alone produces 4.0 cases per request. Any capacity or staffing discussion based on
   request counts will materially under-resource Credentialing.

3. **Automation now originates 28.5% of all requests** — 19,036 from the Re-Credentialing and Ancillary
   Re-Assessment batches and 11,540 from four bot accounts. The Re-Credentialing batch is fully automated:
   all 18,609 re-cred requests were system-generated with zero manual creation.

4. **Batch operations are healthy; batch *monitoring* is not.** Every one of 9,918 batch executions in the
   measurable window completed successfully. But 2.07 million false error records — 97% of the year's entire
   error log — were written by a single misconfigured job, which makes genuine failures effectively invisible
   (§5). Separately, 2,928 network-link records failed and have never been retried.

5. **Four request types cannot be measured by the standard completion field** and are reported separately
   in §2.3. Off-Cycle and PNC in particular show 10% and 1% completion on the request header while their
   underlying cases close at 61% and 49% — a tracking gap, not a performance problem.

---

## 2. Request volume and throughput

### 2.1 Full-year results by request type

| Request type | Team | Received | Completed | Rate | Work items | Items/request |
|---|---|---:|---:|---:|---:|---:|
| PDM Manual Change | PDM | 59,215 | 51,869 | 88% | 59,495 | 1.0 |
| Re-Credentialing | Cred | 18,609 | 18,921 | 102% | 46,373 | 2.5 |
| PAR Form | Cred | 14,502 | 9,337 | 64% | 58,163 | 4.0 |
| Non-Par Claims | PDM | 10,296 | 10,272 | 100% | 10,296 | 1.0 |
| Off-Cycle | Cred | 2,057 | 204 | 10% | 6,262 | 3.0 |
| PNC | Cred | 1,205 | 17 | 1% | 3,446 | 2.9 |
| Non-Participation | PDM | 1,172 | 1,161 | 99% | 2,359 | 2.0 |
| Ancillary Re-Assessment | Cred | 427 | 134 | 31% | 427 | 1.0 |
| Ancillary Assessment | Cred | 131 | 31 | 24% | 322 | 2.5 |
| Provider Change Request | PDM | 70 | 59 | 84% | 127 | 1.8 |
| CMS Preclusion Term | PDM | 2 | 1 | 50% | 3 | 1.5 |
| **Total** | | **107,686** | **92,006** | **85%*** | **187,273** | **1.7** |

\* Completions in period ÷ arrivals in period — a pace ratio across two different populations, not the share
of 2026 arrivals completed. That cohort figure is 66% (71,128 of 107,686); see §2.4.

A further **16,083 cases** exist with no parent request (16,081 already closed), bringing total case volume
to 203,356. These are legacy or system-generated items outside the request lifecycle.

**Re-Credentialing exceeds 100% because completion is measured as an event in the period, not as a cohort.**
18,921 re-creds finished between January and August; 18,609 arrived in that window. The surplus is work
that arrived in late 2025 and finished in 2026. This is the correct way to measure throughput — a
created-and-completed cohort measure would have understated Re-Credentialing and PAR by roughly 3× because
both routinely take longer than a month.

### 2.2 Monthly trend

| Month | Received | Completed | Net |
|---|---:|---:|---:|
| January | 15,989 | 9,229 | −6,760 |
| February | 17,412 | 10,534 | −6,878 |
| March | 13,338 | 9,996 | −3,342 |
| April | 15,053 | 15,038 | −15 |
| May | 11,457 | 8,908 | −2,549 |
| June | 11,461 | 14,836 | **+3,375** |
| July | 12,677 | 12,478 | −199 |
| August | 10,299 | 10,987 | **+688** |
| **Total** | **107,686** | **92,006** | **−15,680** |

The shape of this curve is the report's most encouraging finding. Q1 ran a deficit of roughly 17,000
requests. From April onward the teams reached and held break-even, and June and August were net-positive —
backlog actively reduced. Intake also declined 41% from the February peak (17,412) to August (10,299),
which gave the teams room to catch up.

June's spike is explained by Re-Credentialing: 5,997 completions against a monthly baseline of roughly
2,000, indicating a concerted catch-up effort on the re-cred queue.

### 2.3 Four request types need a different measure

For most request types the completion field on the request header is reliable. For four it is not, and
publishing their headline completion rate without this context would misrepresent the teams' performance.

| Request type | Header completion | Case closure | What is actually happening |
|---|---:|---:|---|
| Off-Cycle | 204 (10%) | 3,809 of 6,262 (61%) | 1,663 of 2,057 requests sit at *Network Management QC*, which functions as the terminal stage. Work finishes; the header is never advanced to Complete. |
| PNC | 17 (1%) | 1,687 of 3,446 (49%) | Same pattern — 768 parked at *Network Management QC*, 360 at *Application Review*. |
| Ancillary Assessment | 31 (24%) | 195 of 322 (61%) | 75 at *PDA Review and Update*; low volume, mixed tracking. |
| Ancillary Re-Assessment | 134 (31%) | 28 of 427 (7%) | **Genuine backlog.** 399 of 427 requests are stalled at *PSV*, and 395 carry status *Pending Application*. This one is a real bottleneck, not a measurement artifact. |

**Recommendation:** for Off-Cycle, PNC and Ancillary Assessment, either advance the request header when the
final case closes, or adopt case closure as the official throughput metric for those types. Ancillary
Re-Assessment needs operational attention rather than a measurement change — 92% of the year's volume has
not moved past primary source verification.

### 2.4 Cohort position — where the 2026 intake stands today

§2.1 counts completion *events* in the window, which includes requests that arrived in late 2025. This table
asks the complementary question: of the requests that arrived **in 2026**, how many are finished **now**?
Source: current `PRM_Stage__c` of all `IndividualApplication` created in the window, treating `Complete` and
`Case Complete` as terminal.

| Request type | Received | Now complete | Still open | % done |
|---|---:|---:|---:|---:|
| Non-Par Claims | 10,296 | 10,264 | 32 | 100% |
| Non-Participation | 1,172 | 1,083 | 89 | 92% |
| PDM Manual Change | 59,215 | 46,548 | 12,667 | 79% |
| Provider Change Request | 70 | 51 | 19 | 73% |
| CMS Preclusion Term | 2 | 1 | 1 | 50% |
| Re-Credentialing | 18,609 | 8,613 | 9,996 | 46% |
| PAR Form | 14,502 | 4,357 | 10,145 | 30% |
| Ancillary Assessment | 131 | 24 | 107 | 18% |
| Off-Cycle | 2,057 | 154 | 1,903 | 7% |
| Ancillary Re-Assessment | 427 | 24 | 403 | 6% |
| PNC | 1,205 | 9 | 1,196 | 1% |
| **Total** | **107,686** | **71,128** | **36,558** | **66%** |

Three types are effectively clear (Non-Par Claims 32 open, Non-Participation 89, Provider Change Request 19).
Three carry 32,808 of the 36,558 open requests: PDM Manual Change 12,667, PAR Form 10,145, Re-Credentialing
9,996. The bottom four percentages are the §2.3 recording gap, not a measure of progress.

**Do not add 36,558 (requests open) to 41,353 (work items open)** — different units, overlapping populations.

### 2.5 Rework

Reopened-and-recompleted requests are a proxy for work that had to be redone:

| Request type | Rework | Of total completions |
|---|---:|---:|
| Off-Cycle | 48 | 19.0% |
| Provider Change Request | 3 | 4.8% |
| Ancillary Re-Assessment | 1 | 0.7% |
| Re-Credentialing | 17 | 0.1% |
| All others | 10 | <0.1% |

**Rework is negligible across the board — 79 instances in 92,006 completions.** Off-Cycle's 19% rate is
worth a look, but on a base of 252 events it represents fewer than 50 requests.

A second signal, stage transitions per completed request, shows where process complexity sits: PAR Form
averages 7.1 handling steps per completion and Re-Credentialing 3.9, against 1.0 for PDM Manual Change and
Non-Par Claims. PNC's 134 transitions per completion is an artifact of the tracking gap in §2.3, not a real
process.

---

## 3. Where the work sits — case-level view

### 3.1 Team workload inversion

| Team | Requests | Share | Work items | Share |
|---|---:|---:|---:|---:|
| Credentialing | 36,931 | 34.3% | 114,993 | **61.4%** |
| Provider Data Management | 70,755 | 65.7% | 72,280 | 38.6% |

PDM's volume is dominated by PDM Manual Change and Non-Par Claims, both of which are effectively
straight-through: one case per request, one handling step, near-zero rework. Credentialing's volume is
concentrated in PAR Form and Re-Credentialing, which require multi-stage review — primary source
verification, quality control, committee review, network management QC.

### 3.2 Open work — what is actually holding it

41,353 work items were open at period end. Decomposed by status, **nine in ten had never been started**:

| Blocking condition | Open items | Share | Constituent statuses |
|---|---:|---:|---|
| Never started | **37,052** | **89.6%** | `New` |
| Waiting on an external party | 2,728 | 6.6% | Pending NPDB 926, NPDB Action Required 824, Returned 569, Pending Application 395, Pending Committee Decision 8, Request for Additional Info 2, Provider Outreach 2, Rebuttal 2 |
| On hold / pended | 882 | 2.1% | On Hold 837, Pended 43, Pended-Processing 1, Pended-Rebuttal Specialist 1 |
| Actively in progress | 639 | 1.5% | In Progress 634, Ready For MD Review 5 |
| Anomalous | 52 | 0.1% | `Complete` but not closed 50, Denied-Appeal Open 2 |
| **Total** | **41,353** | **100%** | |

Only 1.5% of the open backlog is in active work. The constraint is queue intake capacity, not cycle time.
The never-started pile concentrates in four queues: Network Management QC 24,175, PSV 8,515, PDA Review and
Update 2,019, QC Review 1,610.

**Scope:** filtered on the *case's* own `CreatedDate`. Cases created before 1 Jan 2026 and still open are
excluded, so 41,353 is the unfinished remainder of 2026-created work, not the org's total open backlog. The
50 cases at status `Complete` with `IsClosed = false` are the same status/stage inconsistency flagged in
§2.3 — immaterial at this scale.

### 3.3 Open work by queue

| Queue | Open items | Share |
|---|---:|---:|
| Network Management QC | 24,260 | 58.7% |
| PSV (Primary Source Verification) | 11,379 | 27.5% |
| PDA Review and Update | 2,215 | 5.4% |
| QC Review | 1,674 | 4.0% |
| Application Review | 1,098 | 2.7% |
| PNC | 361 | 0.9% |
| Recred Updates | 156 | 0.4% |
| Non-Par QC Review | 108 | 0.3% |
| All other queues | 102 | 0.2% |

**86% of all open work sits in two queues.** Network Management QC alone holds 24,260 items, of which
24,175 are still in *New* status — never picked up. This is the single largest operational concentration in
the report and the obvious first target for capacity planning.

The PSV backlog of 11,379 breaks down as 8,515 never started (75%), 2,251 externally blocked, and 529 in
progress. Within the externally blocked group: 872 await NPDB response, 654 need NPDB action, 395 await
application materials, 330 have been returned. So roughly one in five PSV items is waiting on an external
party — but three in four are waiting on internal capacity, the same condition as Network Management QC.

---

## 4. Administrative batch operations

### 4.1 Scheduled job inventory

**20 scheduled jobs are active; 3 are paused.**

The PRM business-process jobs currently running:

| Scheduled job | Frequency | Cumulative runs |
|---|---|---:|
| PRM Org NPDB Processor | every 2 hours | 1,885 |
| Re-Credentialing | daily | 453 |
| PRM_DailyScheduledFlowToCheckIfCaseHasExpiredOrNot | daily | 455 |
| ProcessFutureDateActivation | daily | 334 |
| ProcessFutureDateTermination | daily | 334 |
| PRM CheckDueOnAncillaryReAssessmentBatch | daily | 252 |
| PRM_NCPDPBatch_Daily_3AM | daily | 140 |
| PRM ReCheckActiveCAQHValidationBatch | weekdays | 121 |
| PRM LetterRecredBatch | daily | 116 |
| PractitionerPNCDailyBatch | daily | 3 |
| PractitionerPSVBatchScheduler | daily | 3 |

Run counts are cumulative since each job was first scheduled, not 2026-only — Salesforce does not retain
per-execution history beyond about 7 days. The two jobs showing 3 runs were deployed in the last few days.

**Three paused jobs require a decision:**

| Paused job | Last ran | Concern |
|---|---|---|
| PRM FutureHCProviderNPIActivateBatch | **never** (0 runs) | Scheduled for June 2025, never executed |
| PRM FutureAddressActivateBatch | 22 July 2025 | Dormant 13 months |
| PRM_ReinitiateNPDBReport | 31 July 2026 | Recently paused |

Future-dated activation may now be handled by `ProcessFutureDateActivation` (334 runs) and
`PRM_FutureDatedProcessingBatch` (25 runs in the last week), in which case the two 2025-era jobs are dead
metadata and should be deleted. That should be confirmed rather than assumed — if they are not superseded,
future-dated address and NPI activations have not been processing for over a year.

### 4.2 Batch execution success

In the trailing 7-day window — the longest period Salesforce retains — **41 batch classes executed 9,918
times with a 100% success rate.** No failed or aborted jobs. The two non-completed entries are schedulers
sitting in *Queued*, which is their normal resting state.

Highest-volume batches in that window:

| Batch class | Runs (7 days) | Purpose |
|---|---:|---|
| PRM_HCPFProcessingBatch | 5,101 | Practitioner-facility relationship processing |
| PRM_HFNProcessingBatch | 2,659 | Healthcare facility network processing |
| PRM_CMACreationBatch | 733 | Case Manager Association creation |
| PRM_LinkPLPPLTNBatch | 530 | Practice location / transaction network linking |
| PRM_PractitionerPNCBatch | 277 | PNC practitioner processing |
| PRM_AddPracPPLTNBatch | 124 | Practitioner practice-location addition |
| PRM_OrgNPDBProcessorBatch | 84 | Organisation NPDB processing |

At 9,918 executions per week the platform runs roughly 1,400 batch jobs per day. Extrapolated across the
period that is on the order of 340,000 executions, though this is an estimate from one week and should not
be published as a precise figure.

### 4.3 What the batches produced

The business asked specifically how many cases the batches created. Attribution by creating account:

| Source | Requests created | Share | Detail |
|---|---:|---:|---|
| Batch automation | 19,036 | 17.7% | Re-Credentialing 18,609 · Ancillary Re-Assessment 427 |
| Bot accounts | 11,540 | 10.8% | Barry Bot 8,316 · Kelly Bot 2,180 · Cuthbert Bot 843 · John Bot 201 |
| **Total automated** | **30,576** | **28.5%** | |
| Human specialists | 76,721 | 71.5% | 69+ named users |

**The Re-Credentialing batch is the single largest automated producer: 18,609 requests, generating 46,373
work items, with zero human-created re-creds all year.** It runs daily and produced roughly 2,100 requests
per month, with an April spike to 4,320. Ancillary Re-Assessment is likewise 100% batch-generated (427).

Bot accounts create PDM Manual Change (9,268 combined), PAR Form (2,158) and PNC (114) — these represent
integration-driven intake rather than scheduled batch generation.

Human workload concentration is worth noting: PDM Manual Change is spread across 32 specialists, Non-Par
Claims across 20, and Non-Participation across 16. PAR Form, by contrast, is handled by only 7 people
despite being the most work-intensive request type in the portfolio, and Off-Cycle by 4.

One record to verify: **Pamela Smith is credited with 10,194 PDM Manual Changes** — 17% of that type and
far above the next-highest individual (3,925). This is either a shared service account or a bulk-load
operator, and should be confirmed before the figure is used in any productivity comparison.

---

## 5. Platform health

Two production defects surfaced during extraction. Neither affects the throughput figures above, but both
affect the organisation's ability to detect failures.

### 5.1 The error log is 97% noise

| Month | Error records |
|---|---:|
| January | 6,748 |
| February | 8,395 |
| March | 112,445 |
| April | 390,220 |
| May | 366,320 |
| June | 373,560 |
| July | 427,073 |
| August | **446,521** |
| **Total** | **2,131,282** |

Against a January–February baseline of ~7,600 per month, August ran **59× higher**. Roughly **2.07 million
records — 97% of the year's entire error log — are excess**, occupying about 4.1 GB of storage.

**Cause: a single job logging a normal condition as an error.** The `PRM Org NPDB Processor` job, scheduled
every two hours, was introduced on **20 March 2026** — the exact date the increase begins. When it examines
a Case Manager that has no adverse action logs, it records an `Error`. Having no adverse action logs is a
normal, expected state for most practitioners. Because the job re-examines the same population every two
hours and that population grows, the volume compounds: ~6,100 records per day in March, ~14,400 per day by
August.

99.9% of the records carry the single message *"No adverse action logs found for Case Manager."* The
genuine failures in the same log — adverse action logs stuck in error status, unprocessed logs — are
outnumbered roughly 1,000 to 1. **In practical terms the organisation has had no usable error monitoring
since 20 March.**

*Fix: treat the no-adverse-action-log case as a normal outcome rather than an error, and restrict the job's
scope to unprocessed records. Purge the historical volume separately.*

### 5.2 2,928 failed records have never been retried

| Failing process | Target | Failed records |
|---|---|---:|
| PRM_LinkPLPPLTNBatch | HealthcareFacilityNetwork | 2,795 |
| PRM_HFNCascadeBatch | HealthcareFacilityNetwork | 72 |
| PRM_NetworkCreationBatch | HealthcareFacilityNetwork | 60 |
| PRM_UpdateHCFNetworkBatch | HealthcareFacilityNetwork | 1 |
| **Total** | | **2,928** |

All 2,928 remain in *Pending* status — none has been retried, resolved or written off. All four processes
write to the same target, and one process accounts for 95%. **2,928 provider-network link records were
never created**, which means silent gaps in network data. Comparison against a May sandbox copy places the
entire backlog after 22 May 2026, making this a second-half regression.

*Fix: establish a retry and monitoring process for this queue, and reprocess the backlog.*

### 5.3 A data-quality note on status reporting

For PDM Manual Change, the `Status` field reports 37,214 complete while the `Stage` field reports 46,548 —
a **9,334-record discrepancy** on the same population. Stage is the more current of the two. Any dashboard
or report built on `Status` will understate PDM completion by roughly 18%. This report uses stage
transitions throughout.

---

## 6. Recommendations

| Priority | Action | Owner | Rationale |
|---|---|---|---|
| 1 | Fix the NPDB processor's error classification and scope | Development | Restores error monitoring lost since 20 March; recovers ~4 GB storage |
| 2 | Establish retry and monitoring for the failed-record queue; reprocess 2,928 records | Development / PDM | Silent provider-network data gaps |
| 3 | Address the Network Management QC backlog — 24,175 items never picked up | Credentialing / PDM leadership | 59% of all open work |
| 4 | Investigate Ancillary Re-Assessment — 399 of 427 stalled at PSV | Credentialing | 92% of the year's volume has not progressed |
| 5 | Align request-header completion with case closure for Off-Cycle, PNC and Ancillary Assessment | Business analysis | Makes throughput reportable for these types |
| 6 | Review PAR Form staffing — 7 people handle the most work-intensive type (4.0 items/request) | Credentialing leadership | Workload concentration risk |
| 7 | Decide on the 3 paused jobs; confirm future-dated activation is not silently broken | Development | Two dormant since mid-2025, one never ran |
| 8 | Correct dashboards that report completion from `Status` rather than `Stage` | Reporting | 9,334-record understatement on PDM Manual Change |

---

## 7. Basis of preparation

**Definitions.** *Request* = one `IndividualApplication` record. *Work item* = one `Case` record.
*Completed* = the request's stage transitioned to `Complete` or `Case Complete` within the period, counted
as a distinct request. *Closed* = case `IsClosed` = true at extraction.

**Period.** 1 January 2026 00:00 UTC to 1 September 2026 00:00 UTC exclusive — 31 August is fully included.

**Throughput is measured as events in the period, not as a created-and-completed cohort.** A cohort measure
would exclude work that arrived in 2025 and finished in 2026, understating Re-Credentialing and PAR Form by
approximately 3× and 2.7× respectively.

**Known limitations.**

- Batch run counts are cumulative since each job was scheduled. Salesforce retains per-execution history
  for approximately 7 days only, so full-year per-batch run counts cannot be produced retrospectively.
  Establishing a durable batch-execution log would enable this in future periods.
- Creator attribution (§4.3) excludes users with 25 or fewer requests of a given type, covering 107,297 of
  107,686 requests (99.6%). The "69+ named users" figure is therefore a floor, not a headcount.
- Provider Change Request (70) and CMS Preclusion Term (2) are excluded from creator attribution for the
  same reason.
- Four request types do not use the standard completion field; see §2.3.
- 16,083 cases have no parent request and are excluded from per-type case figures.

**Reproducibility.** All figures are reproducible from the extraction scripts in `scripts/apex/` and the
consolidation script `scripts/opex/consolidate_prod.py`. Full query definitions, data provenance
verification and 25 documented data caveats are in
[`requirements/SOQL/2026-08-31_OperationalExcellence_2026_Report.md`](SOQL/2026-08-31_OperationalExcellence_2026_Report.md).
