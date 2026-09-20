# Solo Practitioner Group-Join Violations (Individual/Type-1 Group NPI)

**Date:** 2026-08-19
**Context:** New business rule stops a practitioner from joining another solo practitioner's practice location (see `requirements/PAR_OffCycle_SoloPractitioner_GroupJoin_Restriction_UserStory.md`, CQ-7). These queries size the *existing* problem: how many practitioners are already affiliated to a practice location whose group NPI is an individual (Type 1) NPI belonging to somebody else.

**Key data-model facts these queries rely on (all verified against org metadata):**
- A practice location's group NPI is `HealthcareFacility.PRM_NpiId__c` → `HealthcareProviderNpi` (relationship `PRM_NpiId__r`).
- `HealthcareProviderNpi.NpiType` = `Individual` (Type 1, a person) or `Organization` (Type 2, a group). An `Individual` group NPI on a practice location is the solo-practitioner signal.
- `HealthcareProviderNpi` carries both `PractitionerId` (a **Contact**) and `AccountId` (the practitioner's Person Account) — the NPI's owner.
- `HealthcarePractitionerFacility.PractitionerId` is a **Contact** (the practitioner's `PersonContactId`), *not* an Account. Use `Practitioner.AccountId` to get to the Person Account.
- The practitioner-to-practice-location link is record type `PRM_PractitionerLocationAffiliation`. (`PRM_PractitionerPracticeAffiliation` is the practitioner-to-**group** link — different thing.)

---

## Query 1 — Inventory of solo practice locations

**Object:** `HealthcareFacility`
**Use case:** How many practice locations in the org carry an individual (Type 1) NPI as their group NPI, and who owns each one. This is the population the new rule protects.

```sql
SELECT Id, Name, AccountId, Account.Name,
       PRM_NpiId__c,
       PRM_NpiId__r.Npi,
       PRM_NpiId__r.NpiType,
       PRM_NpiId__r.PractitionerId,
       PRM_NpiId__r.AccountId,
       PRM_NpiId__r.Account.Name,
       PRM_Active__c, PRM_EffectiveFrom__c, PRM_EffectiveTo__c
FROM HealthcareFacility
WHERE PRM_NpiId__r.NpiType = 'Individual'
  AND PRM_IsErrorRecord__c = false
  AND RecordType.DeveloperName != 'PRM_NCPDP'
  AND (PRM_Active__c = true
       OR (PRM_Active__c = false AND PRM_EffectiveTo__c = NULL))
ORDER BY Account.Name, Name
```

**Sample result / row count (if known):** Not yet run — run in FC2 first.
**Notes / gotchas:**
- The active-vs-pending predicate mirrors `PRM_RecordQueryServiceUtils.getAccountForNPI`, so the row set matches what the PAR group search would actually return to a specialist.
- `RecordType.DeveloperName != 'PRM_NCPDP'` excludes pharmacy locations, consistent with the group-search Apex.
- `PRM_NpiId__r.Account.Name` is the NPI owner's Person Account name — expect it to look like a person, not a practice.

---

## Query 2 — Candidate violations (superset; needs a client-side compare)

**Object:** `HealthcarePractitionerFacility`
**Use case:** Every active practitioner-to-practice-location link where the location's group NPI is an individual NPI. This is a **superset** — it includes legitimate cases where the practitioner *is* the NPI owner. Filter those out after export.

```sql
SELECT Id, Name,
       PractitionerId, Practitioner.Name, Practitioner.AccountId,
       HealthcareFacilityId, HealthcareFacility.Name,
       HealthcareFacility.AccountId, HealthcareFacility.Account.Name,
       HealthcareFacility.PRM_NpiId__r.Npi,
       HealthcareFacility.PRM_NpiId__r.NpiType,
       HealthcareFacility.PRM_NpiId__r.PractitionerId,
       HealthcareFacility.PRM_NpiId__r.AccountId,
       IsActive, EffectiveFrom, EffectiveTo, PRM_CaseManager__c
FROM HealthcarePractitionerFacility
WHERE RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'
  AND IsActive = true
  AND PRM_IsErrorRecord__c = false
  AND PractitionerId != NULL
  AND HealthcareFacility.PRM_NpiId__r.NpiType = 'Individual'
ORDER BY HealthcareFacility.Account.Name, HealthcareFacility.Name
```

**Sample result / row count (if known):** Not yet run.
**Notes / gotchas:**
- **SOQL cannot compare two fields to each other in a `WHERE` clause.** There is no way to express `PractitionerId != HealthcareFacility.PRM_NpiId__r.PractitionerId` in SOQL — that is why this query returns a superset and the mismatch test has to happen in Apex (Query 3) or a spreadsheet. Do not try to add the comparison to the `WHERE`; it will not compile.
- A row is a **violation** when `Practitioner.AccountId != HealthcareFacility.PRM_NpiId__r.AccountId`.
- Compare on **Account**, not Contact: `HealthcarePractitionerFacility.PractitionerId` and `HealthcareProviderNpi.PractitionerId` are both Contacts and *should* agree, but `HealthcareProviderNpi.PractitionerId` is sometimes null where `AccountId` is populated. Account-level comparison is the more reliable test.
- Drop `IsActive = true` to include future-dated and terminated links if the business wants full history rather than the current-state picture.

---

## Query 3 — Violation count and detail (anonymous Apex, does the field-to-field compare)

**Object:** `HealthcarePractitionerFacility` (via Apex)
**Use case:** Produces the actual violation count and a CSV-ready detail list, performing the comparison SOQL cannot express.

```apex
List<HealthcarePractitionerFacility> candidates = [
    SELECT Id, Name,
           PractitionerId, Practitioner.Name, Practitioner.AccountId,
           HealthcareFacilityId, HealthcareFacility.Name,
           HealthcareFacility.Account.Name,
           HealthcareFacility.PRM_NpiId__r.Npi,
           HealthcareFacility.PRM_NpiId__r.AccountId,
           HealthcareFacility.PRM_NpiId__r.Account.Name,
           EffectiveFrom, EffectiveTo
    FROM HealthcarePractitionerFacility
    WHERE RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'
      AND IsActive = true
      AND PRM_IsErrorRecord__c = false
      AND PractitionerId != NULL
      AND HealthcareFacility.PRM_NpiId__r.NpiType = 'Individual'
];

Integer violations = 0;
Set<Id> affectedPractitioners = new Set<Id>();
Set<Id> affectedLocations = new Set<Id>();
List<String> rows = new List<String>{
    'HCPF_Id,Practitioner,Practitioner_Account,Location,Group,Location_NPI,NPI_Owner'
};

for (HealthcarePractitionerFacility h : candidates) {
    Id ownerAccountId = h.HealthcareFacility.PRM_NpiId__r.AccountId;
    Id pracAccountId  = h.Practitioner.AccountId;

    // Violation = the location's individual NPI belongs to a different practitioner.
    // Null owner is also treated as a violation (fail-safe default, pending CQ-2).
    if (ownerAccountId == null || ownerAccountId != pracAccountId) {
        violations++;
        affectedPractitioners.add(pracAccountId);
        affectedLocations.add(h.HealthcareFacilityId);
        rows.add(String.join(new List<String>{
            h.Id,
            h.Practitioner.Name,
            String.valueOf(pracAccountId),
            h.HealthcareFacility.Name,
            h.HealthcareFacility.Account.Name,
            h.HealthcareFacility.PRM_NpiId__r.Npi,
            h.HealthcareFacility.PRM_NpiId__r.Account.Name
        }, ','));
    }
}

System.debug('Candidate links on solo locations: ' + candidates.size());
System.debug('Violations: ' + violations);
System.debug('Distinct practitioners affected: ' + affectedPractitioners.size());
System.debug('Distinct solo locations involved: ' + affectedLocations.size());
for (String r : rows) { System.debug(r); }
```

**Sample result / row count (if known):** Not yet run.
**Notes / gotchas:**
- Run with `sf apex run --file scripts/apex/<name>.apex` and read the debug log; if the candidate list is large, convert to a Batch class rather than anonymous Apex to avoid the 50,000-row query limit and debug-log truncation.
- The null-owner branch is treated as a violation to match the fail-safe default assumed in AC-4 of the story. If CQ-2 resolves the other way, flip that condition and re-run — the two counts together tell you how much of the total is genuine mismatch versus missing owner data.
- `affectedPractitioners` counts Person Accounts, so it is the number of practitioners the business would have to remediate, not the number of link records.

---

## Query 4 — Solo locations ranked by how many outside practitioners have joined

**Object:** `HealthcarePractitionerFacility`
**Use case:** Prioritises remediation — a solo location with many practitioners attached is the most likely data-entry hot spot and the best candidate for manual review first.

```sql
SELECT HealthcareFacilityId, HealthcareFacility.Name,
       HealthcareFacility.Account.Name,
       HealthcareFacility.PRM_NpiId__r.Npi,
       COUNT(Id) linkCount
FROM HealthcarePractitionerFacility
WHERE RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'
  AND IsActive = true
  AND PRM_IsErrorRecord__c = false
  AND HealthcareFacility.PRM_NpiId__r.NpiType = 'Individual'
GROUP BY HealthcareFacilityId, HealthcareFacility.Name,
         HealthcareFacility.Account.Name,
         HealthcareFacility.PRM_NpiId__r.Npi
HAVING COUNT(Id) > 1
ORDER BY COUNT(Id) DESC
```

**Sample result / row count (if known):** Not yet run.
**Notes / gotchas:**
- `HAVING COUNT(Id) > 1` is the shortcut that makes this useful without a field-to-field compare: a *genuinely* solo practice location should have exactly **one** practitioner attached. Anything above one is suspicious by definition, and anything well above one is almost certainly a violation cluster.
- This does not prove violation (a solo practitioner could legitimately have two link records across effective-date ranges), so treat it as a triage list and confirm against Query 3's output.
- Aggregate queries cannot return `Id`, so use the `HealthcareFacilityId` values to drill into Query 2 filtered by those locations.

---

## Cross-links

- Story: `requirements/PAR_OffCycle_SoloPractitioner_GroupJoin_Restriction_UserStory.md` (CQ-2 governs the null-owner branch; CQ-7 is the reporting ask these queries answer)
- Related NPI-type data anomalies already documented: `requirements/SOQL/2026-07-16_FC2_EffectiveDates_Repro.md` (an Organization group NPI attached to a `PRM_Practitioner` record-type Account — the mirror image of this problem)
- Individual-vs-Organization NPI filtering precedent: `requirements/SOQL/2026-07-31_CAQHIdLength.md`
