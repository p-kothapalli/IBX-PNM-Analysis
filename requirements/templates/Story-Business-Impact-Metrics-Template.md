# Story Business Impact & Metrics — Template Section

> **Purpose:** Drop this section into every new user story (PRM, PNC, PAR, ReCred, PDM, Ancillary, etc.) so prioritization, sequencing, and post-deploy validation all key off the same numbers.
>
> **Where it goes:** Add it directly under the **Story** / **Background** block and *before* **Acceptance Criteria**, so reviewers see the "why this is worth doing" before the "what we'll build."
>
> **Rule of thumb:** If you can't fill in at least one row of the **Quantified Impact** table with a real number from a query, GUS report, or case list — the story is not ready for sprint commit.

---

## Business Impact & Metrics

### A. One-line value statement

> _Doing this will unblock **\<N>** records, close **\<M>** prod tickets, and unblock **\<K>** support cases._

_(Rewrite in plain English — this is the line that goes into sprint review and the release notes.)_

---

### B. Quantified Impact

| # | Impact Dimension                          | Today's Pain (baseline)                              | After This Story (target)        | Delta            | Source / Query                                                                                       | Validated? |
|---|-------------------------------------------|------------------------------------------------------|----------------------------------|------------------|------------------------------------------------------------------------------------------------------|------------|
| 1 | **Records unblocked**                     | _e.g., 4,231 `PRM_HCPF__c` rows with stale `P2P_EffectiveFrom__c`_ | _0 stale; backfill batch will heal all_ | _-4,231 stale_   | `SOQL: SELECT COUNT() FROM PRM_HCPF__c WHERE …`                                                     | ☐ / ☑      |
| 2 | **Prod tickets closed (GUS bugs / IRs)**  | _e.g., 7 open prod bugs tagged `EffectiveFrom`_      | _All 7 closed on deploy_         | _-7_             | _GUS report URL / list of W-IDs (W-12345678, W-12345679, …)_                                         | ☐ / ☑      |
| 3 | **Support cases unblocked**               | _e.g., 23 cases queued in `Provider Ops` waiting on fix_ | _0 in queue_                     | _-23_            | _Case list view URL / saved report_                                                                  | ☐ / ☑      |
| 4 | **Users / orgs impacted**                 | _e.g., ~40 credentialing analysts; all of IBX prod_  | _Same population, unblocked_     | _N/A_            | _Permission set assignment count: `PRM_CredentialingUser`_                                          | ☐ / ☑      |
| 5 | **$ / SLA impact (if known)**             | _e.g., 14-day avg cred SLA breach on delegated providers_ | _Within 7-day SLA_              | _-7 days_        | _Cred Ops weekly report_                                                                             | ☐ / ☑      |
| 6 | **Manual effort eliminated**              | _e.g., 6 hrs/week of manual SOQL data fixes by Ops_  | _0 hrs/week_                     | _-6 hrs/wk_      | _Ops time-tracking sheet / runbook_                                                                  | ☐ / ☑      |

> Mark **Validated** only when the baseline number came from a query/report run within the last 14 days — *not* from memory or a hallway estimate.

---

### C. Records Unblocked — Detail

| Object / Entity                  | Count of Stuck Records | Stuck Because…                                  | Unblocked By This Story (mechanism)        |
|----------------------------------|------------------------|-------------------------------------------------|--------------------------------------------|
| _e.g., `PRM_HCPF__c`_            | _4,231_                | _`P2P_EffectiveFrom__c` set to wrong PPL date_  | _Backfill batch (S-XXX4) + trigger sync_   |
| _e.g., `IndividualApplication`_  | _312_                  | _PNC path skipped for delegated practitioners_  | _IP fix (S-XXX2)_                          |
| _e.g., `PRM_CaseManagerAssoc__c`_| _58_                   | _QC case stuck in "Pending PSV"_                 | _Status auto-advance flow (S-XXX5)_        |

**Total records unblocked:** _\<sum>_

---

### D. Prod Tickets Closed by This Story

| GUS W-ID    | Title (short)                                   | Severity | Status    | Closed by which AC? |
|-------------|-------------------------------------------------|----------|-----------|---------------------|
| _W-12345678_| _"P2P EffectiveFrom shows wrong date on PDP"_   | _Sev 2_  | _Open_    | _AC-1, AC-3_        |
| _W-12345679_| _"Backfill needed for legacy delegated rows"_   | _Sev 3_  | _Open_    | _AC-4_              |
| _W-12345680_| _"Cred analyst sees stale data in QC review"_   | _Sev 2_  | _Open_    | _AC-2_              |

**Total prod tickets closed:** _\<count>_  •  **Sev 1/2 closed:** _\<count>_

---

### E. Support Cases Unblocked

| Case # / Queue              | Count | Theme / Root Cause                          | This Story Resolves It Because…                |
|-----------------------------|-------|---------------------------------------------|------------------------------------------------|
| _Provider Ops queue_        | _17_  | _"EffectiveFrom mismatch reported by SVP"_  | _Backfill closes the data gap retroactively_   |
| _Cred Ops queue_            | _6_   | _"Cred decision blocked by stale P2P date"_ | _Trigger sync prevents recurrence_             |
| _Customer Care escalations_ | _0_   | _N/A_                                       | _N/A_                                          |

**Total cases unblocked:** _\<count>_  •  **Active escalations cleared:** _\<count>_

> Link the case list view or report URL: _\<paste link>_

---

### F. Cost of *Not* Doing This (next 90 days)

| Risk if We Skip / Defer                                                          | Likelihood | Magnitude                              |
|----------------------------------------------------------------------------------|------------|----------------------------------------|
| _Stuck records continue to grow at ~50/week → +650 by EOQ_                       | _High_     | _Ops time, audit risk_                 |
| _Sev 2 ticket reopens during quarterly audit_                                    | _Medium_   | _Audit finding, exec visibility_       |
| _Manual workaround becomes "the process" — institutional knowledge debt_         | _High_     | _Onboarding cost, accuracy_            |

---

### G. Post-Deploy Validation (how we'll *prove* the metrics moved)

| Metric                         | How / Where to Re-measure                    | Owner       | Re-measure on Day… |
|--------------------------------|----------------------------------------------|-------------|--------------------|
| _Records unblocked_            | _Re-run SOQL from row 1 of section B_        | _\<dev>_    | _D+1, D+7, D+30_   |
| _Prod tickets closed_          | _GUS report; verify each W-ID is `Closed`_   | _\<TL>_     | _D+1_              |
| _Cases unblocked_              | _Re-run case list view; expect 0 in queue_   | _\<Ops PM>_ | _D+7_              |
| _SLA / time-to-cred_           | _Cred Ops weekly report_                     | _\<Ops PM>_ | _D+30_             |

> If any post-deploy metric does **not** move as expected, raise a follow-up story or hotfix — do not silently close.

---

### H. Stack-Rank Inputs (for sprint planning)

| Input                                      | Value                                |
|--------------------------------------------|--------------------------------------|
| **Reach** (records + cases + tickets)      | _e.g., 4,261_                        |
| **Severity** (max of involved tickets)     | _Sev 2_                              |
| **Effort** (story points / hrs)            | _e.g., 8 SP / 26 hrs_                |
| **Impact-per-effort score**                | _Reach ÷ hrs = e.g., 164/hr_         |
| **Hard dependency on another story?**      | _Yes — S-XXX1 must deploy first_     |

---

### Authoring checklist (delete before merging the story)

- [ ] Every number in section B has a query, GUS report, or case list link backing it (no estimates from memory).
- [ ] Every W-ID in section D is real and verifiable in GUS.
- [ ] Section E links a saved case list view or report URL.
- [ ] Section G assigns an owner and a re-measure date for *every* metric.
- [ ] The one-line value statement in section A matches the totals in B/C/D/E.
