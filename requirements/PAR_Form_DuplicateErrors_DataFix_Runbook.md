# PAR Form Existing Record Duplicate Errors - Data Fix Runbook

Document Version: 1.0
Created Date: May 22, 2026
Vertical: Provider Network Management (PNM)
Target Org: qa-sandbox (alias)
Companion to: requirements/PAR_Form_ExistingRecord_DuplicateErrors_UserStory.md
Source: Verified against live QA org data on 2026-05-22

---

## Executive Summary

Out of the 16 failure rows recorded in `Copy of Duplicate account and tax id errors.xlsx`, **only 11 (~69%) are cleanly fixable by data alone**. The remaining 5 will keep recurring on every retry until the code/config items in the original user story (`PAR_Form_ExistingRecord_DuplicateErrors_UserStory.md`) ship.

| Category | Failure Rows | Data Fix Viable? | Reason |
|---|---|---|---|
| **C** - HCPT duplicate junction | 10 (rows 5, 7, 8, 9, 11, 12, 13, 14, 17, 19) | YES - Full fix | 5 unique duplicate `(AccountId, TaxonomyId)` pairs. Delete the loser of each pair so DR upsert match returns exactly 1. |
| **A row 3** - George Henry | 1 | YES - Full fix | `HealthcareProviderNpi.AccountId` is NULL. Re-link to existing Account, reactivate Account+HCP. |
| **A row 6** - Melanie Weaver / Acclaim Autism | 1 | Workaround only | Practitioner Account does NOT exist; vendor Account DOES exist - that is the desired state. Form is wrongly trying to recreate the vendor. Resolved by analyst-side process change (search-and-pick vendor) OR pre-staging a Melanie practitioner stub. |
| **B rows 10, 16, 20** - Ovsev / Sandi / Igor | 3 | NO - Recurring bug | Vendor-level HC Provider record. The `populateSourceSystemIdentifier` trigger deterministically generates `TaxId-VendorName` on every PAR submission against that vendor. Deleting the existing HCP fixes ONE submission; the next collides again. |
| **D row 21** - Generic catch-all | 1 | Unknown | Error message masked by OmniScript catch-all. Re-submit with verbose logging to classify into A / B / C, then apply matching fix. |

**After running the data fixes documented here, expected pass rate: 11 of 16 (69 percent).** Cat B and the generic row 21 remain blocked on code fixes. Note that the 3 Cat B rows represent only a snapshot - every future PAR submission against Rittenhouse / AtlantiCare / Advanced Ambulatory will keep failing the same way until the trigger idempotency fix (Item #6 in the user story) ships.

---


## 1. Live Org Verification

All findings below were verified against the `qa-sandbox` org on 2026-05-22 using `sf data query`. Raw query results are saved in `/tmp/parfix/*.json` (gitignored).

### 1.1. Practitioner Accounts (7 queried)

| Account Id | Name | NPI (`HealthCloudGA__SourceSystemId__c`) | Record Type | IsActive | IsPersonAccount |
|---|---|---|---|---|---|
| `001UW00000eiR46YAE` | George K Henry | `1932179090` | PRM_Practitioner | **false** | true |
| `001UW00000eiED1YAM` | Hyesun Lee | `1053793505` | PRM_Practitioner | true | true |
| `001UW00000eivAwYAI` | Erin B McNeilly | `1174744783` | PRM_Practitioner | true | true |
| `001UW00000ej33JYAQ` | Charles E Digby | `1629208095` | PRM_Practitioner | true | true |
| `001UW00000i9PM1YAM` | Amir Hedayati | `1770534869` | PRM_Practitioner | true | true |
| `001UW00000vCYhvYAG` | Bryan P Romero | `1487244414` | PRM_Practitioner | true | true |
| `001UW00000ejxCcYAI` | Acclaim Autism | `844050618-Acclaim Autism` | **PRM_Vendor** | true | **false** |

Cat B practitioner Accounts (discovered via HCNPI follow-up):

| Account Id | Name | NPI | Record Type |
|---|---|---|---|
| `001UW00000eiS5qYAE` | Ovsev Uzuner | `1437203346` | PRM_Practitioner |
| `001UW00000eiSLMYA2` | Sandi McKay | `1972200632` | PRM_Practitioner |
| `001UW00000eiqsnYAA` | Igor Moiseyvich Povzhitkov | `1700924669` | PRM_Practitioner |

**Critical finding**: The user story labeled `001UW00000ejxCcYAI` as the existing Account for row 6 (Melanie Weaver) but that record is actually the **Acclaim Autism vendor**, not Melanie's practitioner account. Melanie has no Account in QA at all. This changes the row-6 fix strategy entirely.

### 1.2. HealthcareProviderNpi state (10 NPIs queried)

| NPI | HCNPI Id | AccountId | IsActive | Status |
|---|---|---|---|---|
| `1932179090` | `0bNUW000001N8ck2AC` | **NULL** | true | **BROKEN LINK** |
| `1801188388` | (none) | - | - | **Missing entirely** (Melanie Weaver) |
| `1053793505` | `0bNUW000001M4Oe2AK` | `001UW00000eiED1YAM` | true | OK |
| `1174744783` | `0bNUW000001MFfQ2AW` | `001UW00000eivAwYAI` | true | OK |
| `1437203346` | `0bNUW000001MsCC2A0` | `001UW00000eiS5qYAE` | true | OK |
| `1487244414` | `0bNUW000001NHy22AG` | `001UW00000vCYhvYAG` | true | OK |
| `1629208095` | `0bNUW000001NPP82AO` | `001UW00000ej33JYAQ` | true | OK |
| `1700924669` | `0bNUW000001NThP2AW` | `001UW00000eiqsnYAA` | true | OK |
| `1770534869` | `0bNUW000001Lu5S2AS` | `001UW00000i9PM1YAM` | true | OK |
| `1972200632` | `0bNUW000001MXmG2AW` | `001UW00000eiSLMYA2` | true | OK |

**Only 1 of 10 NPIs has the broken-link symptom described in the user story** (NPI 1932179090 / George Henry). The other Cat-A row (Melanie Weaver) has no HCNPI at all. The Cat-B HCNPI links are all correctly populated.

### 1.3. HealthcareProvider records (vendor-level - the actual collision target)

The user story's `0bSUW...` IDs do not exist in QA. The colliding records are standard `HealthcareProvider` rows (key prefix `0cm`) keyed by `(VendorAccountId, SourceSystemIdentifier=TaxId-VendorName)`:

| HCP Id | Name | AccountId (Vendor) | SourceSystemIdentifier | Status |
|---|---|---|---|---|
| `0cmUW000001NA2UYAW` | Rittenhouse Imaging Center LLC | `001UW00000ejo3bYAA` | `233067073-Rittenhouse Imaging Center LLC` | Active |
| `0cmUW000001N9PCYA0` | AtlantiCare Physician Group | `001UW00000ejywxYAA` | `020701782-AtlantiCare Physician Group` | Active |
| `0cmUW000001k2bgYAA` | Atlanticare Physician Group PA | `001UW00000gT3vFYAS` | `020701782-Atlanticare Physician Group PA` | Active |
| `0cmUW000001NRr7YAG` | Advanced Ambulatory Anesthesia LLC | `001UW00000ejshFYAQ` | `223683554-Advanced Ambulatory Anesthesia LLC` | Active |
| `0cmUW000001OJloYAG` | Acclaim Autism | `001UW00000ejxCcYAI` | `844050618-Acclaim Autism` | Active |

**Critical finding**: HCPs are **vendor-scoped** (`PractitionerId = NULL`), NOT per-practitioner-per-vendor junctions. Every PAR submission against the same vendor regenerates the same `TaxId-VendorName` value via the trigger and collides on the unique constraint. **Deleting the existing HCP cures one submission and breaks the next.**

For Sandi McKay (TaxId 20701782, 8 digits): the existing record has SSI `020701782-AtlantiCare Physician Group` (zero-padded to 9 chars). The trigger's `TaxId.substring(0,9)` against an 8-char raw value yields `20701782-...` (no zero-pad) - **different** from the stored value. So row 16 may actually be a leading-zero formatting bug rather than a true duplicate. Confirm with the trigger author / Q5 in the user story.

### 1.4. HealthcareProviderTaxonomy duplicates (5 pairs verified)

For each `(AccountId, TaxonomyId)` pair, exactly 2 rows exist. The "winner" of each pair has `IsActive=true`, `PRM_Pending__c=false`, no error flags, and a real `EffectiveFrom` date. The "loser" is a stub.

| Pair | Account | Taxonomy | KEEP (winner) | DELETE (loser) | Loser red flags |
|---|---|---|---|---|---|
| D6 - Hyesun Lee | `001UW00000eiED1YAM` | `0bKUW00000000qI2AQ` | `0bPUW0000007jid2AA` | `0bPUW00000073lx2AA` | Active=false, Pending=true, **IsErrorRecord=true**, no dates |
| D7 - Charles Digby | `001UW00000ej33JYAQ` | `0bKUW00000000hC2AQ` | `0bPUW0000007jzT2AQ` | `0bPUW0000006rXt2AI` | Active=false, Pending=true, no dates |
| D8 - Bryan Romero | `001UW00000vCYhvYAG` | `0bKUW00000000qI2AQ` | `0bPUW0000009pzL2AQ` | `0bPUW0000009a972AA` | Active=false, no dates |
| D9 - Amir Hedayati | `001UW00000i9PM1YAM` | `0bKUW00000000jg2AA` | `0bPUW0000005Nwi2AE` | `0bPUW0000004t7Z2AQ` | Active=false, Pending=true, no dates |
| D10 - Erin McNeilly | `001UW00000eivAwYAI` | `0bKUW00000000qI2AQ` | **BA decision required** | - | See note below |

**D10 (Erin McNeilly) needs a business-analyst decision** because neither row matches the clean "winner profile":
- `0bPUW0000003rJp2AI`: Active=true, Pending=true, IsPrimary=**false**, EffFrom=2023-01-28
- `0bPUW0000008cJR2AY`: Active=**false**, Pending=false, IsPrimary=true, no EffFrom

Recommendation: keep `0bPUW0000003rJp2AI`, set `IsPrimary=true` and `PRM_Pending__c=false` on it, then delete the other. Get BA approval before running.


---

## 2. Per-Scenario Data Fix - Detail

Each fix below is structured as: **Verdict -> Root cause -> Concrete Apex/SOQL -> Why it works (or does not) -> Caveats**.

### 2.1. Category C - HealthcareProviderTaxonomy Duplicate Junctions

**Verdict: FULLY DATA-FIXABLE. 10 of 16 rows resolved.**

#### 2.1.1. Root cause (verified)

5 unique `(AccountId, TaxonomyId)` pairs each have 2 rows in the DB. The DataRaptor Load engine's upsert match returns 2+ records and throws:

```
Duplicated results found for HealthcareProviderTaxonomy
AccountId=001UW... AND TaxonomyId=0bKUW... -
Related Ids: 0bPUW...,0bPUW....
Delete or fix duplicate records before importing.
```

#### 2.1.2. Pre-flight backup (always run first)

```apex
// scripts/apex/backup_hcpt_pairs_qa.apex - run BEFORE any delete
List<HealthcareProviderTaxonomy> snapshot = [
    SELECT Id, AccountId, TaxonomyId, IsActive, IsPrimaryTaxonomy,
           EffectiveFrom, EffectiveTo, PRM_Pending__c, PRM_IsErrorRecord__c,
           SourceSystemIdentifier, CreatedDate, LastModifiedDate
    FROM HealthcareProviderTaxonomy
    WHERE (AccountId='001UW00000eiED1YAM' AND TaxonomyId='0bKUW00000000qI2AQ')
       OR (AccountId='001UW00000ej33JYAQ' AND TaxonomyId='0bKUW00000000hC2AQ')
       OR (AccountId='001UW00000vCYhvYAG' AND TaxonomyId='0bKUW00000000qI2AQ')
       OR (AccountId='001UW00000i9PM1YAM' AND TaxonomyId='0bKUW00000000jg2AA')
       OR (AccountId='001UW00000eivAwYAI' AND TaxonomyId='0bKUW00000000qI2AQ')
];
System.debug(JSON.serializePretty(snapshot));
// Copy the debug output and save as scripts/apex/cleanup_duplicate_hcpt_qa.backup.json
```

Alternatively, export to CSV via the CLI:

```bash
sf data query --target-org qa-sandbox \
  --query "SELECT Id, AccountId, TaxonomyId, IsActive, IsPrimaryTaxonomy, EffectiveFrom, EffectiveTo, PRM_Pending__c, PRM_IsErrorRecord__c, SourceSystemIdentifier, CreatedDate, LastModifiedDate FROM HealthcareProviderTaxonomy WHERE (AccountId='001UW00000eiED1YAM' AND TaxonomyId='0bKUW00000000qI2AQ') OR (AccountId='001UW00000ej33JYAQ' AND TaxonomyId='0bKUW00000000hC2AQ') OR (AccountId='001UW00000vCYhvYAG' AND TaxonomyId='0bKUW00000000qI2AQ') OR (AccountId='001UW00000i9PM1YAM' AND TaxonomyId='0bKUW00000000jg2AA') OR (AccountId='001UW00000eivAwYAI' AND TaxonomyId='0bKUW00000000qI2AQ')" \
  --result-format csv > scripts/apex/cleanup_duplicate_hcpt_qa.backup.csv
```

#### 2.1.3. Cleanup script (4 of 5 pairs - safe to run after BA confirms D10)

```apex
// scripts/apex/cleanup_duplicate_hcpt_qa.apex
// Purpose: Resolve 4 duplicate (AccountId, TaxonomyId) pairs blocking PAR form
//          re-submissions. Excludes D10 (Erin McNeilly) until BA decides which
//          row to keep.
// Effect:  Deletes the "loser" of each pair so DR upsert returns exactly 1 match.
// Backup:  Run scripts/apex/backup_hcpt_pairs_qa.apex first.

Set<Id> losers = new Set<Id>{
    '0bPUW00000073lx2AA',  // D6 Hyesun  - Pending=true, IsErrorRecord=true, no dates
    '0bPUW0000006rXt2AI',  // D7 Charles - Pending=true, Active=false, no dates
    '0bPUW0000009a972AA',  // D8 Bryan   - Active=false, no dates
    '0bPUW0000004t7Z2AQ'   // D9 Amir    - Pending=true, Active=false, no dates
    // 0bPUW0000008cJR2AY  // D10 Erin   - DEFERRED: needs BA decision
};

List<HealthcareProviderTaxonomy> toDelete = [
    SELECT Id, AccountId, TaxonomyId, IsActive, IsPrimaryTaxonomy,
           PRM_Pending__c, PRM_IsErrorRecord__c, EffectiveFrom
    FROM HealthcareProviderTaxonomy
    WHERE Id IN :losers
];

System.debug('=== Pre-delete snapshot ===');
for (HealthcareProviderTaxonomy r : toDelete) {
    System.debug(r);
}

if (toDelete.size() != losers.size()) {
    System.debug(LoggingLevel.ERROR,
        'Expected ' + losers.size() + ' losers but found ' + toDelete.size()
        + '. Aborting to be safe.');
    return;
}

delete toDelete;
System.debug('=== Deleted ' + toDelete.size() + ' rows ===');

// Verify exactly one row remains for each cleaned pair
for (AggregateResult ar : [
    SELECT AccountId, TaxonomyId, COUNT(Id) cnt
    FROM HealthcareProviderTaxonomy
    WHERE (AccountId='001UW00000eiED1YAM' AND TaxonomyId='0bKUW00000000qI2AQ')
       OR (AccountId='001UW00000ej33JYAQ' AND TaxonomyId='0bKUW00000000hC2AQ')
       OR (AccountId='001UW00000vCYhvYAG' AND TaxonomyId='0bKUW00000000qI2AQ')
       OR (AccountId='001UW00000i9PM1YAM' AND TaxonomyId='0bKUW00000000jg2AA')
    GROUP BY AccountId, TaxonomyId
]) {
    Integer cnt = (Integer) ar.get('cnt');
    System.debug(ar.get('AccountId') + ' | ' + ar.get('TaxonomyId') + ' -> ' + cnt);
    if (cnt != 1) {
        System.debug(LoggingLevel.ERROR,
            'PAIR STILL HAS != 1 ROW - investigate before re-submit');
    }
}
```

#### 2.1.4. D10 (Erin McNeilly) - run after BA approval

Recommended path A (keep `0bPUW0000003rJp2AI`, normalize it, delete the other):

```apex
// scripts/apex/cleanup_duplicate_hcpt_d10_pathA.apex
HealthcareProviderTaxonomy keep = new HealthcareProviderTaxonomy(
    Id = '0bPUW0000003rJp2AI',
    IsPrimaryTaxonomy = true,
    PRM_Pending__c = false
);
update keep;

delete new HealthcareProviderTaxonomy(Id='0bPUW0000008cJR2AY');
```

Path B (keep `0bPUW0000008cJR2AY`, reactivate it, delete the other) - only if BA confirms 0008cJR2AY is the canonical record despite IsActive=false:

```apex
// scripts/apex/cleanup_duplicate_hcpt_d10_pathB.apex
HealthcareProviderTaxonomy keep = new HealthcareProviderTaxonomy(
    Id = '0bPUW0000008cJR2AY',
    IsActive = true,
    EffectiveFrom = Date.newInstance(2023, 1, 28),  // copied from sibling
    PRM_Pending__c = false
);
update keep;

delete new HealthcareProviderTaxonomy(Id='0bPUW0000003rJp2AI');
```

#### 2.1.5. Why this works

After cleanup, each `(AccountId, TaxonomyId)` pair has exactly 1 row in the DB. When the analyst re-submits the PAR form:
1. `PRMDRExtractExistingNPIInfo` finds the existing Account + HCNPI -> `IsExistingNPI=true`.
2. Routing -> `PRM_PractitionerScreenExistingNPIRecordUpdation`.
3. `PRMDRCreateTaxonomy` upserts. The composite-key match finds exactly 1 record -> updates the winner row's effective dates -> NO error.

#### 2.1.6. Caveats

1. **Soft delete vs hard delete**: standard Apex `delete` soft-deletes (record moves to Recycle Bin, `IsDeleted=true`). The OmniStudio DR Load engine's match excludes soft-deleted rows by default, so soft-delete is sufficient. If a re-submit still fails with "Duplicated results found", run `Database.emptyRecycleBin(toDelete);` immediately after the delete to hard-purge.
2. **Recycle Bin recovery window**: 15 days. If you discover a wrong row was deleted, restore via `Database.queryAll([SELECT Id FROM HealthcareProviderTaxonomy WHERE Id=:lostId AND IsDeleted=true])` then `undelete`.
3. **Monitoring**: after the trigger from Item #9 of the user story is deployed, this runbook will become unnecessary. Until then, run a weekly count check:

```bash
sf data query --target-org qa-sandbox --query "SELECT AccountId, TaxonomyId, COUNT(Id) cnt FROM HealthcareProviderTaxonomy GROUP BY AccountId, TaxonomyId HAVING COUNT(Id) > 1"
```

Any rows returned indicate new duplicates appeared - notify the dev team.


### 2.2. Category A row 3 - George Henry (NPI 1932179090)

**Verdict: FULLY DATA-FIXABLE.**

#### 2.2.1. Root cause (verified)

Three things are wrong in QA today:

1. `HealthcareProviderNpi` row `0bNUW000001N8ck2AC` exists for NPI 1932179090 but `AccountId = NULL`.
2. The Account `001UW00000eiR46YAE` (George K Henry) has `IsActive = false`.
3. The associated `HealthcareProvider` `0cmUW000001MoMYYA0` has `Status = Inactive`.

`PRMDRExtractExistingNPIInfo` joins HCNPI -> Account on `AccountId`. With `AccountId=NULL`, the join returns no Account -> `PractitionerForm:ExistingAccountId = NULL` -> `IsExistingNPI = false` -> form takes create path -> `PRMDRCreateCaseCaseManagerAndAccount` tries to insert an Account with `HealthCloudGA__SourceSystemId__c='1932179090'` -> unique-External-Id constraint trips on the existing `001UW00000eiR46YAE`.

#### 2.2.2. Pre-flight backup

```bash
sf data query --target-org qa-sandbox \
  --query "SELECT Id, Npi, AccountId, IsActive FROM HealthcareProviderNpi WHERE Id='0bNUW000001N8ck2AC'" \
  --result-format csv > scripts/apex/fix_george_henry.backup.csv
sf data query --target-org qa-sandbox \
  --query "SELECT Id, Name, IsActive, HealthCloudGA__SourceSystemId__c FROM Account WHERE Id='001UW00000eiR46YAE'" \
  --result-format csv >> scripts/apex/fix_george_henry.backup.csv
sf data query --target-org qa-sandbox \
  --query "SELECT Id, Status, AccountId FROM HealthcareProvider WHERE Id='0cmUW000001MoMYYA0'" \
  --result-format csv >> scripts/apex/fix_george_henry.backup.csv
```

#### 2.2.3. Fix script

```apex
// scripts/apex/fix_george_henry_hcnpi_link.apex
// Purpose: Repair the HealthcareProviderNpi -> Account linkage so the PAR form
//          detects existing practitioner Account 001UW00000eiR46YAE and routes
//          to the update path instead of trying to re-create the Account.
// Resolves: Cat A row 3 (Fhnatic case 663776).

// 1. Re-link HCNPI to the existing practitioner Account.
HealthcareProviderNpi hcnpi = [
    SELECT Id, Npi, AccountId, IsActive
    FROM HealthcareProviderNpi
    WHERE Id = '0bNUW000001N8ck2AC'
];
System.debug('HCNPI before: AccountId=' + hcnpi.AccountId);
hcnpi.AccountId = '001UW00000eiR46YAE';
update hcnpi;
System.debug('HCNPI after:  AccountId=' + hcnpi.AccountId);

// 2. Reactivate the practitioner Account. The PAR form's existing-NPI
//    detection may filter on IsActive=true (Q7 in user story).
Account acc = [
    SELECT Id, Name, IsActive, HealthCloudGA__SourceSystemId__c
    FROM Account WHERE Id = '001UW00000eiR46YAE'
];
System.debug('Account before: IsActive=' + acc.IsActive);
acc.IsActive = true;
update acc;
System.debug('Account after:  IsActive=' + acc.IsActive);

// 3. Reactivate the HealthcareProvider so the form's update path can find a
//    non-Inactive HCP record.
HealthcareProvider hcp = [
    SELECT Id, Status, AccountId
    FROM HealthcareProvider WHERE Id = '0cmUW000001MoMYYA0'
];
System.debug('HCP before: Status=' + hcp.Status);
hcp.Status = 'Active';
update hcp;
System.debug('HCP after:  Status=' + hcp.Status);
```

#### 2.2.4. Why this works

After the script runs:
- `PRMDRExtractExistingNPIInfo` joins HCNPI -> Account successfully -> `ExistingAccountId = 001UW00000eiR46YAE`.
- `PRM_FetchExistingNPIInfo` -> `IsExistingNPI = true`.
- `PRM_CreateParFormRecords` routes to `PRM_PractitionerScreenExistingNPIRecordUpdation`.
- `PRMDRPPersonAccHCProviderNPITaxonomyExAcc` (the Existing-Account variant) is invoked, which **omits HealthcareProvider entirely** - no insert, no trigger collision.
- The existing Account, HCP, HCNPI are updated with the new effective dates / case manager.

#### 2.2.5. Caveats

1. **Org policy on inactive Account reuse**: if business policy is "inactive practitioner Accounts must be recreated as new ones rather than reactivated", this fix conflicts with policy. Confirm with BA before running.
2. **Tax-Id mismatch**: if the new PAR submission's Tax-Id differs from any existing Identifier record on this Account, the update path may produce a different error (Q2 in user story). Spot-check the new submission's Tax-Id against `[SELECT IdValue FROM Identifier WHERE ParentId='001UW00000eiR46YAE']`.
3. **No regression risk for clean cases**: this fix only touches one Account / HCNPI / HCP triplet. It does not affect any other practitioner.

### 2.3. Category A row 6 - Melanie Weaver / Acclaim Autism

**Verdict: NOT a clean data-fix scenario. Use process workaround (Option A).**

#### 2.3.1. Root cause (verified)

The user story misidentified this scenario. Live data shows:

- **Melanie Weaver Account does NOT exist** (no Account with `HealthCloudGA__SourceSystemId__c='1801188388'`).
- **Melanie Weaver HCNPI does NOT exist** (no HCNPI with `Npi='1801188388'`).
- **Acclaim Autism vendor Account `001UW00000ejxCcYAI` DOES exist** with `HealthCloudGA__SourceSystemId__c='844050618-Acclaim Autism'` (Tax-Id-Name format, not NPI).

So the colliding record is the **vendor Account**, not a practitioner Account. The form attempted to insert a duplicate vendor Account during the create path, and the External-Id unique constraint trips.

#### 2.3.2. Option A - Process change (recommended; no data change needed)

Tell the analyst:

> "On the Vendor / Group step of the PAR form for case 677637, search by Tax ID `844050618` and select the existing 'Acclaim Autism' vendor instead of choosing 'Create New Vendor'. The new submission will reuse `001UW00000ejxCcYAI` and the form will succeed."

This is the form's intended path. The original analyst likely bypassed the search step.

**Outcome**: form succeeds immediately. No data change. No code change. Zero risk.

#### 2.3.3. Option B - Pre-stage Melanie Weaver records (data fix, but risky)

Only consider this if Option A is not viable (e.g., the form does not actually expose a vendor-search step at this branch).

```apex
// scripts/apex/prestage_melanie_weaver.apex
// WARNING: only use if Option A (process change) is not viable. Without
// associated Identifier and IndividualApplication records, the form's update
// path may still fail downstream in PRM_PractitionerScreenExistingNPIRecordUpdation.

Id practitionerRT = [
    SELECT Id FROM RecordType
    WHERE SObjectType='Account' AND DeveloperName='PRM_Practitioner'
].Id;

Account melanie = new Account(
    FirstName = 'Melanie',
    LastName = 'Weaver',
    HealthCloudGA__SourceSystemId__c = '1801188388',
    RecordTypeId = practitionerRT,
    IsActive = true
);
insert melanie;
System.debug('Created Melanie Weaver Account: ' + melanie.Id);

HealthcareProviderNpi hcnpi = new HealthcareProviderNpi(
    Name = '1801188388',
    Npi = '1801188388',
    AccountId = melanie.Id,
    IsActive = true,
    EffectiveFrom = Date.today()
);
insert hcnpi;
System.debug('Created HCNPI: ' + hcnpi.Id);
```

**What goes right**: the form now sees `IsExistingNPI=true`, routes to update path, does not try to create a new Acclaim Autism vendor (because the existing-Account variant DR uses the existing vendor lookup).

**What can go wrong**:
- The update path (`PRM_PractitionerScreenExistingNPIRecordUpdation`) expects to UPDATE Identifier and IndividualApplication records that do not exist. It may throw a `LIST has no rows for assignment to SObject` error.
- The Practitioner Person-Contact backing the Person Account may be missing custom-field values that downstream LWCs require for display.

**Recommendation**: **do not run Option B in QA without a sandbox safety dry-run on a separate Account first.**

#### 2.3.4. Option C - Wait for code fix

Story Items #1, #2, #3 (broaden existing-record detection + add `PRMDREAccountByNpi` safety branch) are designed to handle exactly this case. Once Phase 3 of the rollout plan ships, the analyst's original create-path submission will detect the existing vendor automatically.

### 2.4. Category B rows 10 / 16 / 20 - Vendor-level HC Provider collision

**Verdict: NOT data-fixable. Workarounds available but not sustainable.**

#### 2.4.1. Root cause (verified)

The colliding `HealthcareProvider` records are vendor-scoped (`PractitionerId=NULL`, `AccountId=<vendor>`):

- Rittenhouse Imaging Center LLC: `0cmUW000001NA2UYAW`, SSI `233067073-Rittenhouse Imaging Center LLC`
- AtlantiCare Physician Group: `0cmUW000001N9PCYA0`, SSI `020701782-AtlantiCare Physician Group`
- Advanced Ambulatory Anesthesia LLC: `0cmUW000001NRr7YAG`, SSI `223683554-Advanced Ambulatory Anesthesia LLC`

The form's create-path DR `PRMDRPPersonAccHCProviderNPITaxonomy` inserts a new `HealthcareProvider` with `AccountId = <vendor Account>`. Before-insert, `PRM_HCProviderTriggerHandler.populateSourceSystemIdentifier` deterministically computes:

```
SourceSystemIdentifier = identifier.IdValue + '-' + acc.Name
                       = TaxId of Vendor Account + '-' + Vendor Account Name
```

For any practitioner participating with Rittenhouse, this evaluates to `233067073-Rittenhouse Imaging Center LLC` - exactly matching the existing record's SSI - and the unique constraint trips.

#### 2.4.2. Why data fix does not work sustainably

If you delete the existing `0cmUW000001NA2UYAW` (Rittenhouse HCP):
1. The current pending submission for Ovsev Uzuner succeeds (one-time win).
2. The very next analyst submitting any practitioner against Rittenhouse re-creates the same `233067073-Rittenhouse Imaging Center LLC` HCP.
3. The submission AFTER that one collides again.
4. Net effect: you have moved the failure from Ovsev to whoever submits next. **Worse**, the original Rittenhouse HCP that was deleted may have been pointed to by other downstream records (Cases, IndividualApplications), so its deletion can cascade-break unrelated workflows.

#### 2.4.3. Diagnostic check before any workaround

The HCNPI links for all 3 Cat B practitioners are correctly populated (see Section 1.2). So `IsExistingNPI` *should* be `true` and the form should take the update path that omits HealthcareProvider creation. Yet the form went down the create path. Two likely explanations:

1. **PNC-Delegated flag**: the `IsExistingNPI` formula is `IF(IsCredentialedPNCDelegated, NULL, IF(ExistingAccountId != NULL, true, false))`. All 3 rows note "Provider cred in progress" - this flag may have been true during the failure window, forcing the create path.
2. **Stale `Identifier` records**: `PRMDRExtractExistingNPIInfo` also joins `Identifier`. If Identifier rows are missing or out of sync, the upstream join may not produce `ExistingAccountId` even when HCNPI is populated.

**Action**: enable trace flag for the analyst, ask them to re-run, examine the `IsCredentialedPNCDelegated` and `ExistingAccountId` values in the OmniScript JSON before deciding any workaround.

#### 2.4.4. Workaround B-1 - One-time admin unblock (use sparingly)

If business absolutely needs row 10 (or 16, or 20) submitted now and cannot wait for the code fix:

```apex
// scripts/apex/onetime_unblock_rittenhouse_hcp.apex
// SHORT-TERM ONLY. The next PAR submission against this vendor may collide
// again. Coordinate with all teams before running.

// 1. Identify any downstream references to the existing HCP. If any exist
//    (Cases, IAs), STOP and reassign them first.
List<Case> casesRef = [SELECT Id, CaseNumber FROM Case WHERE PRM_HealthcareProvider__c = '0cmUW000001NA2UYAW'];
System.debug('Cases referencing this HCP: ' + casesRef.size());
if (!casesRef.isEmpty()) {
    System.debug(LoggingLevel.ERROR, 'STOPPING - downstream Case references must be reassigned first');
    return;
}

// 2. Soft-delete the existing HCP so the trigger insert does not collide.
delete new HealthcareProvider(Id='0cmUW000001NA2UYAW');
System.debug('HCP soft-deleted. Analyst can re-submit case 698724 now.');

// 3. After analyst re-submits, the form will create a new HCP with the same
//    SSI. That is the new canonical record. Note its Id from the success log
//    and update any external references that pointed to the old Id.
```

**Risks**:
- Cascade-broken references to the deleted HCP.
- Next submission against same vendor (any practitioner, by any analyst) re-collides - the deletion only buys one submission.
- The custom field name `PRM_HealthcareProvider__c` in the diagnostic SOQL above is illustrative; verify the actual lookup field on Case before running.

#### 2.4.5. Workaround B-2 - Disable the trigger temporarily

Some orgs expose a Custom Setting flag like `PRM_TriggerSettings__c.DisableHCProviderTrigger__c`. If yours does, toggle it ON, have the analyst submit, then toggle it OFF.

**Risks**:
- All HCP inserts during the window bypass `populateSourceSystemIdentifier`, leaving SSIs blank or wrong on every record created during the window.
- Other downstream logic that reads `SourceSystemIdentifier` will misbehave for those records permanently.
- Verify the flag exists; if it does not, do not deploy a new one just for this - the user-story code fix (Item #6) is a better path.

#### 2.4.6. Real fix

Story Item #6 (idempotency in `populateSourceSystemIdentifier`) and Item #5 (DR upsertKey on `SourceSystemIdentifier`). Both are required. Once shipped, the trigger detects an existing HCP with the computed SSI and either reuses or politely errors with a recoverable validation message instead of the platform DUPLICATE_VALUE.

### 2.5. Category D row 21 - Generic catch-all

**Verdict: Cannot data-fix without classification.**

#### 2.5.1. Diagnostic procedure

```bash
# 1. Enable a TraceFlag on the analyst's user with FINEST Apex+Workflow logging.
sf apex log tail --target-org qa-sandbox --debug-level FINEST &

# 2. Have the analyst re-submit the failing PAR case.

# 3. Read the resulting log; look for:
#    - DUPLICATE_VALUE (likely Cat A or B)
#    - "Duplicated results found" (Cat C)
#    - any other DML error
```

#### 2.5.2. Routing the result

| Log signal | Apply fix | Section |
|---|---|---|
| `DUPLICATE_VALUE: HealthCloudGA__SourceSystemId__c` on Account | A row 3 pattern OR A row 6 pattern depending on whether record is practitioner or vendor | 2.2 / 2.3 |
| `DUPLICATE_VALUE: SourceSystemIdentifier` on HealthcareProvider | Cat B - workaround only | 2.4 |
| `Duplicated results found for HealthcareProviderTaxonomy` | Cat C cleanup | 2.1 |
| Anything else | Escalate to dev team | - |


---

## 3. Per-Failure-Row Resolution Map

This is the source-of-truth row-by-row mapping. Cross-reference this with the user story's `Per-Row Issue -> Fix Mapping` table.

| Excel Row | Fhnatic Case | Provider | NPI | Cat | Data Fix | Section | Expected outcome on re-submit |
|---|---|---|---|---|---|---|---|
| 3 | 663776 | George Henry | 1932179090 | A | Run `fix_george_henry_hcnpi_link.apex` | 2.2 | Form detects existing Account, takes update path, succeeds |
| 5 | 673515 | Hyesun Lee | 1053793505 | C | Run `cleanup_duplicate_hcpt_qa.apex` | 2.1 | DR upsert finds 1 match (winner row), succeeds |
| 6 | 677637 | Melanie Weaver | 1801188388 | A | Option A: analyst uses vendor search | 2.3.2 | Form reuses Acclaim Autism vendor, succeeds |
| 7 | 695317 | Charles E Digby | 1629208095 | C | Run `cleanup_duplicate_hcpt_qa.apex` | 2.1 | DR upsert succeeds |
| 8 | 695435 | Bryan Romero | 1487244414 | C | Run `cleanup_duplicate_hcpt_qa.apex` | 2.1 | DR upsert succeeds (D8 pair) |
| 9 | 697360 | Amir Hedayati | 1770534869 | C | Run `cleanup_duplicate_hcpt_qa.apex` | 2.1 | DR upsert succeeds (D9 pair) |
| 10 | 698724 | Ovsev Uzuner | 1437203346 | B | None (data fix not viable) | 2.4 | Will keep failing until trigger idempotency fix ships |
| 11 | 699856 | Amir Hedayati | 1770534869 | C | Same fix as row 9 | 2.1 | Success after row-9 cleanup runs |
| 12 | 701509 | Bryan Romero | 1487244414 | C | Same fix as row 8 | 2.1 | Success after row-8 cleanup runs |
| 13 | 701737 | Erin McNeilly | 1174744783 | C | D10 cleanup script - **needs BA decision** | 2.1.4 | DR upsert succeeds after BA-approved path runs |
| 14 | 703594 | Bryan Romero | 1487244414 | C | Same fix as row 8 | 2.1 | Success |
| 16 | 708088 | Sandi McKay | 1972200632 | B | None - also possibly leading-zero bug (Q5) | 2.4 | Blocked on code fix |
| 17 | 711166 | Amir Hedayati | 1770534869 | C | Same fix as row 9 | 2.1 | Success |
| 19 | 712069 | Hyesun Lee | 1053793505 | C | Same fix as row 5 | 2.1 | Success |
| 20 | 674985 | Igor Povshitkov | 1700924669 | B | None | 2.4 | Blocked on code fix |
| 21 | n/a | (unknown) | - | D | Diagnose first | 2.5 | Reroute to A / B / C fix once classified |

**Summary**: 11 rows resolve via data-fix (rows 3, 5, 7, 8, 9, 11, 12, 13, 14, 17, 19). 5 rows do not (rows 6 needs process change not data; rows 10, 16, 20 are blocked on code; row 21 needs diagnosis first).

Note that row 6 succeeds via process change (analyst uses vendor search), so business can effectively unblock 12 of 16 cases without code changes if they accept the workaround for row 6.

---

## 4. Execution Runbook

### 4.1. Order of operations

| Step | Command | Owner | Risk | Rollback |
|---|---|---|---|---|
| 1. Backup HCPT pairs | `sf apex run --file scripts/apex/backup_hcpt_pairs_qa.apex --target-org qa-sandbox` | Dev | None (read-only) | n/a |
| 2. Backup George Henry triplet | run the SOQL block in Section 2.2.2 | Dev | None | n/a |
| 3. Get BA decision on D10 (Erin) | n/a | BA | None | n/a |
| 4. Run Cat C cleanup (4 of 5 pairs) | `sf apex run --file scripts/apex/cleanup_duplicate_hcpt_qa.apex --target-org qa-sandbox` | Dev | Low - Recycle Bin restore within 15 days | `Database.queryAll(... WHERE IsDeleted=true)` then `undelete` |
| 5. Run D10 cleanup | run BA-approved variant from Section 2.1.4 | Dev | Low | Recycle Bin |
| 6. Run George Henry fix | `sf apex run --file scripts/apex/fix_george_henry_hcnpi_link.apex --target-org qa-sandbox` | Dev | Low - reversible via single update DML | re-run with original `AccountId=NULL`, `IsActive=false`, `Status='Inactive'` |
| 7. Brief analyst on row 6 vendor-search workaround | n/a | Ops/Training | None | n/a |
| 8. Have each analyst re-submit their failed PAR case | Browser | QA Analyst | None | n/a |
| 9. Diagnose row 21 (Section 2.5) | trace flag | Dev | None | n/a |
| 10. Communicate Cat B rows 10/16/20 status to business | n/a | Product | n/a | n/a |

### 4.2. Verification queries (run after Steps 4-6)

```bash
# Confirm Cat C duplicates resolved (should return 0 rows for fixed pairs)
sf data query --target-org qa-sandbox --query "SELECT AccountId, TaxonomyId, COUNT(Id) cnt FROM HealthcareProviderTaxonomy WHERE (AccountId='001UW00000eiED1YAM' AND TaxonomyId='0bKUW00000000qI2AQ') OR (AccountId='001UW00000ej33JYAQ' AND TaxonomyId='0bKUW00000000hC2AQ') OR (AccountId='001UW00000vCYhvYAG' AND TaxonomyId='0bKUW00000000qI2AQ') OR (AccountId='001UW00000i9PM1YAM' AND TaxonomyId='0bKUW00000000jg2AA') OR (AccountId='001UW00000eivAwYAI' AND TaxonomyId='0bKUW00000000qI2AQ') GROUP BY AccountId, TaxonomyId HAVING COUNT(Id) > 1"

# Confirm George Henry HCNPI link is now correct
sf data query --target-org qa-sandbox --query "SELECT Id, Npi, AccountId FROM HealthcareProviderNpi WHERE Id='0bNUW000001N8ck2AC'"

# Confirm Account is Active
sf data query --target-org qa-sandbox --query "SELECT Id, Name, IsActive FROM Account WHERE Id='001UW00000eiR46YAE'"
```

Expected: Cat C query returns 0 rows; HCNPI shows `AccountId=001UW00000eiR46YAE`; Account shows `IsActive=true`.

### 4.3. End-to-end smoke test (recommended)

For at least one fixed case in each category, have the analyst re-submit the original PAR in QA and verify success. Suggested coverage:

| Category | Test case | NPI | Vendor | Expected |
|---|---|---|---|---|
| A | Case 663776 (George Henry) | 1932179090 | (any) | Form prefills, Final Submit succeeds, no DUPLICATE_VALUE error |
| C | Case 673515 (Hyesun Lee) | 1053793505 | PM Pediatrics of Livingston | Form succeeds, DR upsert returns 1 match for HCPT |
| C | Case 695435 (Bryan Romero) | 1487244414 | Central Jersey Urgent Care LLC | Same |

If all 3 pass, the data fix is verified for production rollout.

### 4.4. Production rollout

This runbook is QA-specific (record IDs are `0bPUW...` etc. in QA). For production:

1. Re-run all SOQL queries in Section 1 against the production org to identify the prod-equivalent record IDs. The duplicate pattern is data-driven and the IDs WILL differ.
2. Repeat the Cat C cleanup with prod IDs.
3. Apply the George Henry fix only if the same broken-link symptom exists in prod.
4. Same vendor-search guidance applies in prod for row-6-style cases.
5. Cat B (rows 10, 16, 20) workarounds: do **not** apply in prod. Wait for the code fix to be deployed.

---

## 5. Open Questions / Dependencies

| # | Question | Owner | Blocks |
|---|---|---|---|
| 1 | D10 (Erin McNeilly) - which row to keep? Path A (keep `0bPUW0000003rJp2AI`, normalize) or Path B (keep `0bPUW0000008cJR2AY`, reactivate)? | BA | row 13 fix |
| 2 | Row 6 (Acclaim Autism) - is the form's vendor-search step exposed at the failure branch, or do we need the practitioner-stub workaround? | Product/UX | row 6 unblock |
| 3 | Cat B - is the Sandi McKay TaxId 20701782 case actually a leading-zero bug (`020701782` vs `20701782`) rather than a true duplicate? Confirm by re-reading `populateSourceSystemIdentifier` substring logic. | Dev | row 16 classification |
| 4 | Is `IsCredentialedPNCDelegated=true` on any of the Cat B failure submissions? | Dev (trace) | Cat B routing analysis |
| 5 | Org policy: are inactive practitioner Accounts allowed to be reactivated? (Affects George Henry fix.) | BA | row 3 fix |
| 6 | Custom-Setting flag for trigger bypass - does one exist? Do not deploy a new one. | Dev | Cat B workaround viability |
| 7 | When Cat B code fix (Items #5, #6) ships, when do the 3 blocked submissions (Ovsev, Sandi, Igor) get re-attempted? | Product | end-to-end resolution |

---

## 6. References

- Source user story: `requirements/PAR_Form_ExistingRecord_DuplicateErrors_UserStory.md`
- Source Excel: `Copy of Duplicate account and tax id errors.xlsx` (May 2026)
- Related: `requirements/PAR_DeniedTerminated_RecordReuse_User_Stories.md`, `requirements/PAR_Form_PNC_Path_User_Stories.md`
- Apex scripts (this runbook): `scripts/apex/cleanup_duplicate_hcpt_qa.apex`, `scripts/apex/fix_george_henry_hcnpi_link.apex`, `scripts/apex/backup_hcpt_pairs_qa.apex`
- Live org snapshot used: `qa-sandbox` (`prashanth.kothapalli@ibx.com.pie.qa`), 2026-05-22
