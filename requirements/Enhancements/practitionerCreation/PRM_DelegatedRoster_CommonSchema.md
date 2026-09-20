# PRM Delegated Roster — Common Orchestrator Schema (v1.1)

**Date:** 2026-07-30
**Status:** Draft for team review
**Purpose:** Define **one canonical JSON envelope** that the roster-upload LWC/adapter sends to the
async roster **framework/orchestrator**, regardless of vendor file layout. Vendor column-name
differences are absorbed by a **mapping profile** (`PRM_VendorRosterMapping__mdt`) upstream — the
orchestrator only ever sees this envelope.

**Grounding:** derived from **12 real vendor roster files** and cross-checked against
`docs/implementation-plan/PRM_RosterUpload_UI_DesignPlan.md` (§2A operation model) and
`requirements/Enhancements/practitionerCreation/PractitionerCreation_FileUpload_DesignPlan.md`
(§5 canonical envelope / IP contract). Where this schema **extends** the existing 4-operation
design, it is called out explicitly in §5.

---

## 0. Files analyzed (12)

| # | File (vendor) | Rows | Directive column(s) | Operation(s) observed |
|---|---|---|---|---|
| 1 | Minute Clinic Initial Cred | 10 | `Comments` | ADD_TO_LOCATION, ADD_TO_ALL_LOCATIONS |
| 2 | Cooper 09/12/25 Updates | 138 | `Comments` + `COMMENTS` | ADD_TO_LOCATION, ADD_NEW_ADDRESS, REMOVE, CHANGE_* |
| 3 | Cooper 05/14/26 Updates Pg2 | 107 | `IBX Comments` + `COMMENTS` | ADD_TO_LOCATION ×54, REMOVE_FROM_LOCATION ×44, exceptions |
| 4 | Cooper 01/12/26 Resubmission | 21 | `IBX Comments` + `COMMENTS` | ADD_TO_LOCATION |
| 5 | Cooper 02/10/26 Delegation | 286 | `Comments` + `COMMENTS` | CREATE ("add provider"/"Add as a New Provider") |
| 6 | Virtua Apr/May 2025 (.xls) | 106 | `Comments` (free text) | CREATE, ADD_TO_LOCATION, ADD_NEW_ADDRESS, add-to-TIN |
| 7 | Jeffcare/JUP/MAHC/vRad | 64 | `Comments` (free text) | CREATE, ADD_TO_LOCATION, ADD_NEW_ADDRESS |
| 8 | NovaCare IBC Providers | 7 | sentinel cell | ADD_TO_ALL_LOCATIONS |
| 9 | UPHS DelegatedFile May Pt2 (Case 660603) | 64 (2 sheets) | `Type of Request` | CREATE_GROUP ("New Group"), ADD_TO_LOCATION ("Add Location") |
| 10 | Princeton PO Terminations (Case 684509) | 28 | `Comments` + `Reason for Termination` | REMOVE (scope=CONTRACT), TERM_GROUP (scope=GROUP) |
| 11 | Vista 694671 Term (Case 724646) | 30 | `Comments` | REMOVE_FROM_LOCATION (scope=AFFILIATION / GROUP), exception |
| 12 | HMH Roster w/ Medicare Flags | 7,386 loc-rows · 3,111 practitioners · 173 vendors | flag column + network code (no per-row directive) | TERM_NETWORK (network 2181 "Amerihealth PPO Medicare") |

**Structural facts the schema must absorb:**
- **Column names differ per vendor** (`Comments` vs `IBX Comments` vs `Provider NPI` vs `NPI NUMBER`…) → mapping-profile concern, not schema.
- **Cooper needs TWO directive columns** (`IBX Comments` = verb, `COMMENTS` = target group NPI/TIN).
- **Cooper/Vista/HMH use internal reference IDs** (`Practitioner PIE`, `Practice Location`, `Vendor`) with a literal `create record` / `-1` sentinel when the record doesn't exist yet → resolve by-ID-or-create.
- **One practitioner spans many rows** (one per location) → group by NPI into one practitioner + `locations[]`.
- **Some files have NO per-row directive** (HMH) — the operation is a **file-level constant + a flag/network selection**.

---

## 1. Request-type catalog

| Operation | Real directive examples | Meaning | Needs Case Manager? |
|---|---|---|---|
| `CREATE` | "Create new provider…", Cooper `create record` | New practitioner (± new group/location) | Yes |
| `CREATE_GROUP` | UPHS "New Group" (Vendor BSPA = -1, has Contract Parent) | New vendor group/TIN, optional hierarchy parent | Yes |
| `ADD_TO_LOCATION` | "Link provider to group location #N", Cooper "add to location", "add to the Group NPI …", Virtua "add to VMG Tax ID" | Existing practitioner gains an affiliation (existing or new address) | Yes / reuse |
| `ADD_TO_ALL_LOCATIONS` | Minute Clinic "…all locations", NovaCare "ADD TO ALL LOCATIONS" | Fan out to every active location of the vendor (group NPI + TIN) | Yes |
| `REMOVE_FROM_LOCATION` | Cooper "remove from location", Vista "Term provider from group and location", Princeton "Terminate PROVIDER from … contract" | End an affiliation; may trigger last-man-standing | No |
| `TERM_NETWORK` | HMH Medicare flag + network code 2181 | End **one** network membership; **affiliation stays** | No |
| `CHANGE_DEMOGRAPHIC` / `CHANGE_SPECIALTY` / `CHANGE_GROUP` / `CHANGE_TIN` / `CHANGE_ADDRESS` | Cooper "Change Last Name from X to Y", "Change group npi from X to Y", "Update location from Ste 503 to Ste 505" | Field-level update on an existing affiliation (old→new pair) | No |
| `EXCEPTION` (status, not an op) | "not listed at npi", "unable to change group NPI…", "No provider listed" | Data-quality/triage flag — round-trips, not actioned | — |

**ADD_NEW_ADDRESS** is modeled as `ADD_TO_LOCATION` with `locationMatch: "NEW_ADDRESS"` (Jeffcare/Virtua/Cooper
"add new address and link" / "add address to group").

---

## 2. Termination is a 4-scope concept

Termination is **not** one thing. Every remove/term op carries a `termination.scope`:

| Scope | Source | Backend effect |
|---|---|---|
| `AFFILIATION` | Cooper/Vista "from group and location" | End `HealthcarePractitionerFacility` (+ its networks); may trigger last-man-standing |
| `GROUP` | Princeton "Terminate GROUP/TIN", Vista "from Group" | End the whole group/TIN affiliation (explicit last-man-standing) |
| `CONTRACT` | Princeton "from Princeton contract" | End membership in a specific contract/PO |
| `NETWORK` | HMH (term 1 network from ~1,264 providers) | End **one** `HealthcareFacilityNetwork` only; affiliation + other networks survive |

---

## 3. Canonical envelope

```jsonc
{
  "schemaVersion": "1.1",
  "submission": {
    "submissionId": "<uuid>",
    "vendorProfile": "UPHS_DELEGATED",
    "vendorAccountId": "001...",
    "processName": "Delegated Roster",
    "caseNumber": "660603",
    "sourceFile": { "name": "...", "contentVersionId": "068...", "sheet": "New Group", "rowCount": 15 },
    "defaults": { "practitionerCreationType": "Delegated Credentialing", "effectiveFrom": "2025-06-01" },
    "networks": ["<HealthcareNetworkId>"],
    "selection": {                                 // flag/query-driven bulk ops (HMH) — no per-row directive
      "mode": "FLAG",                              // FLAG | QUERY | EXPLICIT_ROWS
      "flagColumn": "Vendor or Pract has Medicare",
      "flagValue": "Yes",
      "networkCode": "2181",
      "networkName": "Amerihealth PPO Medicare"
    }
  },
  "practitioners": [
    {
      "rowRef": { "sourceRows": [1] },
      "identity": {
        "individualNpi": "1568442424",
        "practitionerRef": { "type": "PIE_ID", "value": "10000148642" },  // or {"type":"CREATE"} | null for group-level term
        "firstName": "Thanaa", "lastName": "Abraham", "degree": "MD"
      },
      "recordsToUpdate": { /* existing IP contract (FileUpload DesignPlan §5) — CREATE/ADD only */ },
      "group": {
        "groupNpi": "1386431278", "groupTaxId": "23-2777286",
        "groupRef": { "type": "BSPA", "value": "-1" },                    // -1/null ⇒ new group
        "operation": "CREATE_GROUP",
        "parentRef": { "type": "MED_SVC_ENTITY", "value": "004304335" },  // group hierarchy (UPHS Contract Parent)
        "contract": { "name": "Princeton PO", "ref": "..." }
      },
      "locations": [
        {
          "locationRef": { "type": "PIE_ID", "value": "30000003381" },    // or {"type":"CREATE"}
          "operation": "TERM_NETWORK",
          "locationMatch": "EXISTING",                                    // EXISTING | NEW_ADDRESS | ALL | UNKNOWN
          "effectiveDate": "2025-07-01",
          "address": { "line1": "882 H Commons Way", "city": "Toms River", "state": "NJ", "zip": "08757",
                       "standardized": null, "matchedFacilityId": null },
          "networkTargets": [
            { "networkCode": "2181", "networkName": "Amerihealth PPO Medicare", "networkId": "<resolved>" }
          ],
          "termination": {
            "scope": "NETWORK",                     // AFFILIATION | GROUP | CONTRACT | NETWORK
            "termDate": "2025-11-01",               // distinct from effectiveDate
            "reason": "Group leaving Princeton PO",
            "contractRef": "Princeton PO",
            "lastManStanding": "AUTO",              // AUTO | FORCE_END_GROUP | AFFILIATION_ONLY
            "endNetworkMembershipsOnly": true       // true ⇒ keep affiliation (HMH)
          },
          "changes": [ /* CHANGE_* ops only: {field, from, to} */ ]
        }
      ],
      "status": "PENDING",                          // PENDING | READY | WARNING | ERROR
      "exceptions": [
        { "code": "NO_PROVIDER_LISTED", "sourceText": "No provider listed", "severity": "WARNING", "locationIndex": 0 }
      ]
    }
  ]
}
```

---

## 4. How the framework consumes it

- `submission` → `PRM_AsyncJob__c` (one run); `practitioners[]` → `PRM_AsyncJobRecords__c`
  (one per Case Manager); `locations[].operation` selects the batch class;
  `processName` → `PRM_AsyncJobConfig__mdt` sequence.
- `recordsToUpdate` is the **existing IP payload nested verbatim** (FileUpload DesignPlan §5.1),
  so CREATE/ADD reuse the production backend.
- `ADD_TO_ALL_LOCATIONS` and `submission.selection` (HMH) are **expanded server-side** before
  enqueue (`PRM_IPUtility.VendorPracLocations` / network query) so the async job scope is
  deterministic; ~1,264-provider network terms run on the Batch tier.

---

## 5. Deltas vs the existing design (`PRM_RosterUpload_UI_DesignPlan.md` §2A)

The current design models **only 4 operations** (CREATE / ADD_TO_LOCATION / ADD_TO_ALL_LOCATIONS /
REMOVE). This schema adds, grounded in the new files:

1. **`CREATE_GROUP`** + group hierarchy `parentRef` — UPHS "New Group".
2. **`TERM_NETWORK`** with `endNetworkMembershipsOnly` — HMH (must **not** end the affiliation).
3. **`termination.scope`** (AFFILIATION / GROUP / CONTRACT / NETWORK) — Princeton + Vista + HMH.
4. **`CHANGE_*` family** with old→new `changes[]` — Cooper (≈15–20% of Cooper rows).
5. **`submission.selection`** for flag/query-driven bulk files with no per-row directive — HMH.
6. **`status` + `exceptions[]`** channel for data-quality flags — Cooper/Vista.
7. **`contract`** dimension — Princeton PO.

---

## 6. Open questions for the team

1. **`TERM_NETWORK` needs its own backend lane** — network-scope term ends only
   `HealthcareFacilityNetwork`, **not** the affiliation. Confirm the design adds this routing.
2. **`CHANGE_*` family (Cooper) is not in the current 4-op design** — in scope for v1?
3. **Flag/query-driven files (HMH)** — confirm the mapping profile supports
   "operation = constant + target set = flag/network query."
4. **Contract dimension (Princeton)** — model contract/PO as a first-class ref, or fold into group/TIN?
5. **`lastManStanding` default** — AUTO end the group/location/networks, or require explicit analyst
   confirmation in triage?
