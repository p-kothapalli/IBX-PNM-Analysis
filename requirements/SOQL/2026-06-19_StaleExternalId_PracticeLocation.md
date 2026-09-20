# Stale External ID — Practice Location Duplicate Block (Diagnostics)

**Date:** 2026-06-19
**Context:** The `PRM_ExternalId__c` / `SourceSystemIdentifier` composite key embeds the address
at creation time. When a location is terminated/relocated, the key keeps the old address, and a
new location at the old address regenerates the same key — colliding on the unique/externalId
constraint. These queries size the blast radius (target org: `IBXQA` / qa-sandbox).

---

## Query 1 — Practice Location totals & active split

**Object:** `HealthcareFacility`
**Use case:** Baseline volume and how many records are inactive (hold a "locked" key).

```sql
SELECT PRM_Active__c, COUNT(Id) total
FROM HealthcareFacility
GROUP BY PRM_Active__c
```

**Sample result:** Active = 372,149 · Inactive = 10,442 · Total = 382,591

---

## Query 2 — Terminated practice locations (end-dated)

**Object:** `HealthcareFacility`
**Use case:** Count keys frozen by a termination (the relocation/PDM-update scenario).

```sql
SELECT COUNT(Id) c FROM HealthcareFacility WHERE PRM_EffectiveTo__c != null
-- already terminated:
SELECT COUNT(Id) c FROM HealthcareFacility WHERE PRM_EffectiveTo__c < TODAY
-- inactive AND end-dated in the past:
SELECT COUNT(Id) c FROM HealthcareFacility WHERE PRM_Active__c = false AND PRM_EffectiveTo__c < TODAY
```

**Sample result:** HasEffectiveTo = 6,752 · EffectiveTo<TODAY = 6,657 · Inactive+EffTo<TODAY = 6,612

---

## Query 3 — Downstream derived-key volumes

**Object:** `HealthcareFacilityNetwork`, `PRM_HealthcareFacilityNPI__c`, `Account`
**Use case:** Size objects whose key is derived from the HCF external id (inherit the stale address).

```sql
SELECT COUNT(Id) c FROM HealthcareFacilityNetwork
SELECT COUNT(Id) c FROM PRM_HealthcareFacilityNPI__c
SELECT COUNT(Id) c FROM Account
```

**Sample result:** HealthcareFacilityNetwork = 8,858,808 · PRM_HealthcareFacilityNPI__c = 382,143 · Account = 580,194

**Notes / gotchas:**
- `HealthcareFacility.PRM_ExternalId__c` → `unique = true`, `externalId = true` (hard unique index **and** upsert key — this is the blocker).
- `HealthcareFacilityNetwork.SourceSystemIdentifier` → `unique = true`, `externalId = false` (inherits HCF key).
- `PRM_HealthcareFacilityNPI__c.PRM_ExternalId__c` → `unique = false`, `externalId = true` (upsert key only).
- A `COUNT()` with a non-selective filter on `HealthcareFacilityNetwork` (8.8M rows) can time out — add an indexed filter or use a date bound.
