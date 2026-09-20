# Public Group Members

**Date:** 2026-07-10
**Context:** Retrieve the members (users and nested groups) belonging to a Salesforce public group.

---

## Query 1 — Members of a specific public group (by API name)

**Object:** `GroupMember`
**Use case:** List every member entry of a single public group, identified by its stable DeveloperName (API name).

```sql
SELECT Id, GroupId, Group.Name, Group.DeveloperName, UserOrGroupId
FROM GroupMember
WHERE Group.DeveloperName = 'My_Public_Group'
```

**Notes / gotchas:**
- `UserOrGroupId` is polymorphic — a member can be a **User** OR **another Group** (public groups can be nested). You cannot dot-walk relationship fields off it directly in SOQL.
- Filter on `Group.DeveloperName` (stable API name), not `Group.Name` (label, mutable).

---

## Query 2 — Members of all public groups only

**Object:** `GroupMember`
**Use case:** Restrict to true public groups (exclude queues, roles, territory groups) by filtering on `Group.Type = 'Regular'`.

```sql
SELECT Id, GroupId, Group.Name, Group.DeveloperName, Group.Type, UserOrGroupId
FROM GroupMember
WHERE Group.Type = 'Regular'
```

**Notes / gotchas:**
- `Group.Type` values: `Regular` (public group), `Queue`, `Role`, `RoleAndSubordinates`, `RoleAndSubordinatesInternal`, `Territory`, `Organization`, etc. Only `Regular` = public group.

---

## Query 3 — Resolve members to Users (names/emails)

**Object:** `GroupMember`
**Use case:** Get human-readable user details for direct User members of a public group.

```sql
SELECT UserOrGroupId, User.Name, User.Username, User.Email, User.IsActive
FROM GroupMember
WHERE Group.DeveloperName = 'My_Public_Group'
  AND UserOrGroupId IN (SELECT Id FROM User)
```

**Notes / gotchas:**
- The `User.Name` dot-walk only resolves for member rows where `UserOrGroupId` is a User. Rows where the member is a nested Group will not resolve via the `User` relationship.
- For **effective** membership (flattening nested groups + role hierarchy), query `GroupMember` recursively or use the `Group.Type` + nested-group expansion in Apex — a single SOQL cannot flatten nested groups automatically.

---

## Query 4 — Which groups is a given user in (by Username)

**Object:** `GroupMember`
**Use case:** Given a single username, list all groups that user directly belongs to.

```sql
SELECT GroupId, Group.Name, Group.DeveloperName, Group.Type
FROM GroupMember
WHERE UserOrGroupId IN (
    SELECT Id FROM User WHERE Username = 'jane.doe@example.com'
)
```

**Notes / gotchas:**
- Returns **direct** memberships only — not nested-parent groups nor role-derived membership.

---

## Query 5 — Which public groups (only) is a given user in

**Object:** `GroupMember`
**Use case:** Same as Query 4 but restricted to true public groups (`Type = 'Regular'`), excluding queues/roles/territories.

```sql
SELECT GroupId, Group.Name, Group.DeveloperName
FROM GroupMember
WHERE Group.Type = 'Regular'
  AND UserOrGroupId IN (
      SELECT Id FROM User WHERE Username = 'jane.doe@example.com'
  )
```

**Notes / gotchas:**
- Direct memberships only. A user can also belong to a public group **implicitly** if the group's members include her Role or "Roles and Subordinates" — those are computed via the role hierarchy and won't appear as `GroupMember` rows for the user directly.
- To flatten nested groups + role-derived membership, expand recursively in Apex.

---

## Query 6 — Which queues is a given user in (by Username)

**Object:** `GroupMember`
**Use case:** Queues are `Group` records with `Type = 'Queue'`; find the queues a user directly belongs to.

```sql
SELECT GroupId, Group.Name, Group.DeveloperName, Group.Type
FROM GroupMember
WHERE Group.Type = 'Queue'
  AND UserOrGroupId IN (
      SELECT Id FROM User WHERE Username = 'carolyn.norwood@ibx.com'
  )
```

**Notes / gotchas:**
- Direct membership only — role-derived or public-group-derived queue membership won't show as a `GroupMember` row for the user Id.

---

## Query 7 — Queues a user is in, with the objects each queue supports

**Object:** `QueueSobject`
**Use case:** Same as Query 6 but also returns which SObjects each queue is assigned to (Case, Lead, custom objects, etc.).

```sql
SELECT QueueId, Queue.Name, SobjectType
FROM QueueSobject
WHERE QueueId IN (
    SELECT GroupId FROM GroupMember
    WHERE Group.Type = 'Queue'
      AND UserOrGroupId IN (
          SELECT Id FROM User WHERE Username = 'carolyn.norwood@ibx.com'
      )
)
```

**Notes / gotchas:**
- `QueueSobject` maps a queue (`QueueId` → `Group`) to the object types it can own records for.
- To include role/group-derived queue membership, first resolve the user's Role Id and her group memberships, then query `GroupMember` where `Group.Type = 'Queue'` and `UserOrGroupId` is any of those Role/Group Ids.

