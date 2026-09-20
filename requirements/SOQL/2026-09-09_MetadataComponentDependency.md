# Metadata Component Dependency (Salesforce-native dependency graph)

**Date:** 2026-09-09
**Context:** The `code-review-graph` MCP cannot parse Apex or Salesforce metadata XML, so it cannot supply
structural grounding (`callers_of` / `callees_of` / `tests_for`) for this estate. The Tooling API object
`MetadataComponentDependency` is the org-native substitute: it returns real dependency edges across
ApexClass, CustomField, CustomObject, ApexPage, FlexiPage, AuraDefinitionBundle and CustomTab, and it is
authoritative because it comes from the org itself.

All queries below **require `--use-tooling-api`**.

---

## Query 1 — Confirm the dependency object is queryable

**Object:** `MetadataComponentDependency` (Tooling API)
**Use case:** Smoke-test that the org exposes the Dependency API before relying on it.

```sql
SELECT MetadataComponentType, RefMetadataComponentType
FROM MetadataComponentDependency
LIMIT 3
```

**Sample result:** `CustomTab → FlexiPage`, `CustomObject → AuraDefinitionBundle`, `CustomObject → FlexiPage`
**Notes / gotchas:** Fails without `--use-tooling-api`.

---

## Query 2 — Any Apex-sourced dependency edges

**Object:** `MetadataComponentDependency`
**Use case:** Confirm Apex is covered by the dependency graph (the thing `code-review-graph` cannot do).

```sql
SELECT MetadataComponentName, MetadataComponentType,
       RefMetadataComponentName, RefMetadataComponentType
FROM MetadataComponentDependency
WHERE MetadataComponentType = 'ApexClass'
LIMIT 5
```

**Sample result:** `SiteLoginControllerTest → SiteLoginController (ApexClass)`, `SiteRegisterController → SiteRegisterConfirm (ApexPage)`
**Notes / gotchas:** `MetadataComponentType` **is** filterable; the `*Name` fields are **not** (see Query 3).

---

## Query 3 — `callers_of` a class (who depends on it)

**Object:** `ApexClass`, then `MetadataComponentDependency`
**Use case:** The `callers_of` pattern. Name fields are not filterable, so resolve the Id first, then filter on
`RefMetadataComponentId`.

```sql
-- step 1: resolve the class Id
SELECT Id FROM ApexClass WHERE Name = 'PRM_CMAService'
-- -> 01pVB000004ZzO5YAK

-- step 2: who references it
SELECT MetadataComponentName, MetadataComponentType
FROM MetadataComponentDependency
WHERE RefMetadataComponentId = '01pVB000004ZzO5YAK'
```

**Sample result (2 rows):**

| MetadataComponentName | Type |
|---|---|
| `PRM_CMAServiceTest` | ApexClass |
| `PRM_ParFormCmaBatch` | ApexClass |

**Notes / gotchas:**
- This doubles as the **`tests_for`** pattern — the test class shows up as a caller.
- **Material finding:** `PRM_ParFormCmaBatch` proves the **PAR flow already calls `PRM_CMAService`**, i.e.
  `PRM_CaseManagerAssociation__c` already has a shared write path. This answers Clarification Question 7 on
  `requirements/PRM_CaseManagerAssociation_CommonService_UserStory.md`.

---

## Query 4 — `callees_of` a class (what it depends on)

**Object:** `MetadataComponentDependency`
**Use case:** The `callees_of` pattern — dependencies of a component, including fields and objects.

```sql
SELECT RefMetadataComponentName, RefMetadataComponentType
FROM MetadataComponentDependency
WHERE MetadataComponentId = '01pVB000004ZzO5YAK'   -- PRM_CMAService
```

**Sample result (5 rows):**

| RefMetadataComponentName | Type |
|---|---|
| `PRM_CaseManager` | CustomField |
| `PRM_RequestType` | CustomField |
| `PRM_CaseManagerAssociation` | CustomObject |
| `PRM_FormSubUtility` | ApexClass |
| `PRM_ServiceBase` | ApexClass |

**Notes / gotchas:** Confirms `PRM_CMAService extends PRM_ServiceBase` and uses `PRM_FormSubUtility`, and that
`PRM_RequestType__c` is genuinely written by the service (relevant to Clarification Question 3).

---

## Known limits of `MetadataComponentDependency`

| Limit | Consequence |
|---|---|
| `MetadataComponentName` / `RefMetadataComponentName` are **not filterable** | Resolve the component Id first, then filter on `MetadataComponentId` / `RefMetadataComponentId` |
| `COUNT()` is **not supported** | Retrieve rows and count client-side |
| Requires `--use-tooling-api` | Plain `sf data query` returns `INVALID_TYPE` |
| Edges are **deploy-time metadata references**, not runtime call paths | Dynamic `Type.forName` / `Callable` dispatch (e.g. `PRM_AsyncOrchestrator` resolving batch classes) will **not** appear |

> The last row matters for this project: the async framework resolves batch classes by name from
> `PRM_AsyncJobConfig__mdt`, so the orchestrator→batch edges are invisible to this graph and must be read from
> the Custom Metadata rows instead.

---

## CLI form used

```bash
export SF_DISABLE_LOG_FILE=true      # sandbox cannot write ~/.sf/*.log
sf data query --use-tooling-api -o ibx-qa -q "<query>"
```
