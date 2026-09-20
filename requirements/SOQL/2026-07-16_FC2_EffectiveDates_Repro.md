# FC2 Repro — "Effective Dates must be within Account's Effective Dates" (existing-NPI path)

**Date:** 2026-07-16
**Org:** FC2 / fullcopy2 (`prashanth.kothapalli@ibx.com.pie.fullcopy2`, `00DcW000005NtYnUAK`, alias `FC2`)
**Context:** Reproduce the effective-date error on the PAR form. QA runtime capture (2026-07-16, Lucy Tan) proved the **new-practitioner** path does NOT throw (identifiers created with null dates). Goal here: confirm the **existing-NPI** path is the one that throws, and capture the exact stamped date + failing DML step.

---

## Setup done
- Trace flag on user `005UW00000EJHZqYAP` (me), DebugLevel `Finest` (`7dlUW0000000dz3YAA`), TraceFlag `7tfcW000000FxhJQAS`, active 2026-07-16 17:05–21:05 UTC.

## Key finding while selecting candidates
- The "backdated NPI" practitioners (NPI `EffectiveFrom` far predates account `PRM_EffectiveFrom__c`) do **NOT** currently have a backdated **Identifier** — the old date lives only on `HealthcareProviderNpi`. Their existing `Identifier` rows (CAQH) are all **in-window** (= account date).
- Therefore submitting one of them **empirically answers** whether the existing-NPI submit path stamps the backdated NPI date onto an NPI Identifier (→ throws) or leaves it null (→ passes like the new-practitioner path).

## Best repro candidates (participating, active, individual practitioners; NPI predates account)
| Rank | Practitioner | Individual NPI | NPI EffectiveFrom | Account | Account EffFrom | Backdate |
|---|---|---|---|---|---|---|
| 1 | Rayna Sobieski | 1487185963 | 1988-01-01 | 001UW00000pzviNYAQ | 2026-03-07 | ~38 yrs |
| 2 | Ifrana Zaman | 1659892024 | 1987-03-01 | 001UW000015Uo5gYAC | 2024-08-09 | ~37 yrs |
| 3 | Tasha Skinner | 1760900666 | 1992-12-14 | 001UW00000k8PpzYAE | 2025-09-13 | ~33 yrs |
| 4 | Abraham Po-han Houng | 1649226135 | 1995-02-08 | 001UW00000tv6H9YAI | 2026-04-01 | ~31 yrs |
| — | Ammar Taha | 1992032577 | 2009-12-18 | 001UW00000nyz1CYAQ | 2026-05-15 | ~16 yrs |

(133 such candidates found in FC2 via `HealthcareProviderNpi` NpiType=Individual, active participating account, NPI EffectiveFrom < 2024-01-01, account EffFrom > 2024-06-01.)

## Repro steps (UI)
1. Open the PAR form in FC2.
2. Search the practitioner by **existing NPI** (e.g., `1487185963` — Rayna Sobieski) so the existing-NPI path loads.
3. Add/join an active group + primary practice location; complete required screens.
4. Submit. Note the Case Manager number and whether the "Effective Dates must be within Account's Effective Dates" error appears.
5. Tell me "done" — I'll pull the newest debug log and extract: (a) whether the error fires, (b) the exact `PRM_EffectiveFrom__c` written + on which object, (c) the parent Account window it's compared to, (d) the class/step doing the failing DML.

## FC2 baseline — Lucy Tan (NEW practitioner, HMHMG Specialty Care), submitted 2026-07-16 17:19 UTC
Control run to confirm FC2 == QA behavior. **Result: passed, no error** (matches QA):
- Account `001cW00000VWJ8vQAH` (Lucy Tan): `PRM_EffectiveFrom__c = null`, `PRM_EffectiveTo__c = null`, `IsActive=false`, `PRM_Pending__c=true`.
- Identifier `0hkcW000004kWVdQAM` (CAQH 16174844): `PRM_EffectiveFrom__c = null`, `PRM_EffectiveTo__c = null`.
- Record-creation Queueable `07LcW00000KP09SUAT` (18.8 MB): no `addError` / `FIELD_CUSTOM_VALIDATION` / fatal.
- FutureHandler logs `07LcW00000KO7T8UAL`, `07LcW00000KPFBdUAP`: `PRM_IdentifierTriggerHandler` ran (constant `ERR_MSG_INVALIDIDENDATES` loaded at line 71) but did **not** throw.
- **Conclusion:** new-practitioner path creates identifiers with null dates → `null < acct.from` is false → passes. Next: run **Rayna Sobieski** (existing NPI `1487185963`) to test the existing-NPI path.

## PROD FAILURE ANALYSIS (spreadsheet "Effective Date Error HMHMG 7-17-26.xlsx", 2026-06-27 -> 07-15)
- **111 failed submissions, 100 unique practitioners, 100% the SAME group**: group NPI `1215989249`, TIN `223376459` (HMHMG Specialty Care). All "Error : Effective Dates must be within Account's Effective Dates".
- => Not a per-practitioner problem. **Group-level data defect.** Every join to this group fails.

### Root-cause data anomaly (found in FC2, full copy)
- Group NPI `1215989249` = `HealthcareProviderNpi 0bNUW000001MOzW2AW`, **NpiType=Organization, EffectiveFrom `2015-08-01`**.
- It is attached to account **`001UW00000eiFSEYA2` = "GRACE CHANG"**, RecordType **`PRM_Practitioner`** (an *individual*), `PRM_EffectiveFrom__c = 2021-06-21`.
  - i.e. the Org group NPI's effective date (`2015-08-01`) is ~6 years BEFORE its own account's window (`2021-06-21`) => out-of-window.
  - Also structurally wrong: an **Organization** NPI is parented to an **individual practitioner** account, not to the group.
- The actual group account practitioners select is **`001UW00000ejvzDYAQ` = "HMHMG Specialty Care"** (`PRM_Vendor`, window `1995-05-01`), which has **NO Org NPI of its own**. The form passes `ExistingGroupNPIId = 0bNUW000001MOzW2AW` (the GRACE CHANG one).
- `HealthcareProviderNpi.PRM_EffectiveDateValidation` VR = **inactive** => the throw is the **Identifier trigger** (`PRM_IdentifierTriggerHandler`), i.e. the join stamps an NPI-type Identifier `1215989249` @ `2015-08-01` under the `2021-06-21` account.
- There are currently **0** Identifiers with IdValue `1215989249` (consistent with the insert failing every time).

### Why Lucy passed but prod fails
- Lucy (NEW practitioner) join created only her own Individual NPI `1083240014` with null dates; the group Org NPI `1215989249` was never copied/materialized => no throw.
- Sample of prod failing NPIs mostly **pre-exist** as individual accounts => prod failures are the **existing-NPI path**, which pulls the group Org NPI's `2015-08-01` date. That is the path to reproduce.

## Verification query (identifiers created/updated during submit)
```sql
SELECT Id, PRM_Type__c, IdValue, PRM_EffectiveFrom__c, PRM_EffectiveTo__c, ParentRecordId, LastModifiedDate
FROM Identifier
WHERE ParentRecordId = '<practitioner account id>'
ORDER BY LastModifiedDate DESC
```
