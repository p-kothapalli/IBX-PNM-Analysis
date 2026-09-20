# Epic A — Environment Setup (Implementation Guide)

> **Parent:** `PRM_IBC_HighVolume_TDD.md` (§11.2) · `PRM_Implementation_Plan.md` (EPIC A)
> **Goal:** stand up the **net-new async data model + config + access** the Practitioner Creation rebuild depends on. This is pure declarative metadata (objects, fields, Custom Metadata, permission set) — no Apex.
> **Estimate:** ~1.0 engineer-day · **Depends on:** none · **Blocks:** EPIC C (async framework), EPIC E (async processor).

> **⚠ Naming decision (ratified):** to match the org convention (every PRM custom object/field is `PRM_`-prefixed, PascalCase, no inter-word underscores), the async objects are `**PRM_AsyncJob__c` / `PRM_AsyncJobDetails__c`** with `PRM_*` fields — **not** the unprefixed `Async_Job__c` used in the parent TDD/plan. The parent docs still carry the old names and must be reconciled (tracked as a follow-up).

> **Decisions applied:** child→parent = **Master-Detail**; `PRM_CaseManager__c` = **Lookup(IndividualApplication)**; payload/result JSON kept as a **ContentVersion file** on `PRM_AsyncJob__c` (no `InputJson`/`Response` fields); OWD = **Private**; new permission set `**PRM_AsyncJob_Access`**.

---

## A0. Prerequisites & conventions

- SFDX project (`force-app/main/default`), authorized target org, deploy via `sf project deploy start`.
- Field convention (grounded to org): `PRM_` + PascalCase, no underscores between words (e.g. `PRM_BatchSize__c`, `PRM_ProcessName__c`) — matches `PRM_RetryCount__c`, `PRM_RequestPayload__c`, `PRM_ItemsProcessed__c` on existing objects.
- "Case Manager" = the `**IndividualApplication**` record (grounded: `PRM_CaseDataManager__c.PRM_CaseManager__c` and `PRM_FailedRecordStaging__c.PRM_CaseManager__c` are both Lookup→IndividualApplication).

---

## A1 · Object — `PRM_AsyncJob__c` (parent job)

- **Label / Plural:** Async Job / Async Jobs · **OWD:** Private · **Deployment Status:** Deployed · **Allow Reports / Activities:** Reports yes.
- **Name field:** Auto Number, format `AJ-{0000000}`.


| Field API            | Label        | Type                            | Spec                                                   | Req     | Notes                                  |
| -------------------- | ------------ | ------------------------------- | ------------------------------------------------------ | ------- | -------------------------------------- |
| `PRM_CaseManager__c` | Case Manager | Lookup(`IndividualApplication`) | delete = SetNull                                       | No      | correlation to the IA (= Case Manager) |
| `PRM_ProcessName__c` | Process Name | Picklist                        | `Practitioner Creation` · `PAR` (no default)           | **Yes** | restricted; routing key                |
| `PRM_Status__c`      | Status       | Picklist                        | `Queued`(default) · `Running` · `Completed` · `Failed` | **Yes** | restricted picklist                    |


> **Payload storage:** the request/result JSON is **kept as a file (ContentVersion) linked to the `PRM_AsyncJob__c` record**, not in a field — so there is **no `PRM_InputJson__c` / `PRM_Response__c`** on this object. The processor (EPIC C) reads/writes that file.

**Example field metadata** (`objects/PRM_AsyncJob__c/fields/PRM_Status__c.field-meta.xml`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>PRM_Status__c</fullName>
    <label>Status</label>
    <type>Picklist</type>
    <required>true</required>
    <valueSet>
        <restricted>true</restricted>
        <valueSetDefinition>
            <sorted>false</sorted>
            <value><fullName>Queued</fullName><default>true</default><label>Queued</label></value>
            <value><fullName>Running</fullName><default>false</default><label>Running</label></value>
            <value><fullName>Completed</fullName><default>false</default><label>Completed</label></value>
            <value><fullName>Failed</fullName><default>false</default><label>Failed</label></value>
        </valueSetDefinition>
    </valueSet>
</CustomField>
```

---

## A2 · Object — `PRM_AsyncJobDetails__c` (child work item)

- **Label / Plural:** Async Job Details / Async Job Details · **OWD:** Controlled by Parent (Master-Detail) · **Name field:** Auto Number `AJD-{0000000}`.


| Field API            | Label        | Type                                 | Spec                                                   | Req     | Notes                                          |
| -------------------- | ------------ | ------------------------------------ | ------------------------------------------------------ | ------- | ---------------------------------------------- |
| `PRM_AsyncJob__c`    | Async Job    | **Master-Detail**(`PRM_AsyncJob__c`) | reparent = false                                       | **Yes** | parent; cascade delete supports EPIC C cleanup |
| `PRM_CaseManager__c` | Case Manager | Lookup(`IndividualApplication`)      | SetNull                                                | No      | correlation                                    |
| `PRM_ProcessName__c` | Process Name | Text(255)                            | —                                                      | **Yes** | routing key                                    |
| `PRM_Mode__c`        | Mode         | Picklist                             | `Queueable`(default) · `Batch`                         | **Yes** | restricted                                     |
| `PRM_BatchSize__c`   | Batch Size   | Number(4,0)                          | default 200                                            | No      | chunk size for Batch/Queueable chunking        |
| `PRM_Status__c`      | Status       | Picklist                             | `Queued`(default) · `Running` · `Completed` · `Failed` | **Yes** | restricted                                     |
| `PRM_RetryCount__c`  | Retry Count  | Number(2,0)                          | default 0                                              | No      | incremented on retry                           |


> **No `PRM_InputJson__c` / `PRM_Response__c`** on the child either — chunk payload/result are handled via the parent's ContentVersion file (EPIC C).

> **Master-Detail note:** the parent (`PRM_AsyncJob__c`) must exist before children; the EPIC C trigger creates children after the parent insert (same transaction or chained). Cascade delete is relied on by the EPIC C cleanup batch.

---

## A3 · Custom Metadata — `PRM_AsyncJobConfig__mdt`




| Field API                 | Label              | Type        | Spec                            | Notes                                                                                                           |
| ------------------------- | ------------------ | ----------- | ------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `PRM_ProcessName__c`      | Process Name       | Picklist    | `PAR` / `Practitioner Creation` | the process this config applies to (matches `PRM_AsyncJob__c.PRM_ProcessName__c`)                               |
| `PRM_ServiceClassName__c` | Service Class Name | Text(255)   | required                        | Apex class implementing `PRM_AsyncProcessor` that the dispatcher instantiates (`Type.forName`) — resolves CL-12 |
| `PRM_Mode__c`             | Mode               | Picklist    | `Queueable` / `Batch`           | dispatch mode                                                                                                   |
| `PRM_BatchSize__c`        | Batch Size         | Number(4,0) |                                 | chunk size                                                                                                      |
| `PRM_Sequence__c`         | Sequence           | Number(3,0) |                                 | child sequencing (was Chain Order)                                                                              |


---

## A4 · Reused (no change) — `PRM_FailedRecordStaging__c` (DLQ)

Existing object; **do not recreate**. EPIC C's `logFailure` writes to it. Fields used: `PRM_Status__c`, `PRM_RetryCount__c`, `PRM_RequestPayload__c`, `PRM_ErrorMessage__c`, `PRM_ExceptionLog__c`, `PRM_ParentRecordId__c`, `PRM_TargetObject__c`, `PRM_SourceFlow__c`, `PRM_CaseManager__c` (Lookup→IndividualApplication). Confirm the running user/permission set has CRUD here.

**New field to add** (the only change to this existing object):


| Field API                | Label            | Type                             | Spec             | Req | Notes                                                         |
| ------------------------ | ---------------- | -------------------------------- | ---------------- | --- | ------------------------------------------------------------- |
| `PRM_AsyncJobDetails__c` | Async Job Detail | Lookup(`PRM_AsyncJobDetails__c`) | delete = SetNull | No  | links a staged failure back to the child job that produced it |


---

## A5 · Permission Set — `PRM_AsyncJob_Access`

> Permission sets are **not currently tracked in this repo** (`permissionsets/` empty) — this introduces the folder.

- **Objects:** `PRM_AsyncJob__c`, `PRM_AsyncJobDetails__c` → Read/Create/Edit/Delete; `PRM_FailedRecordStaging__c` → Read/Create/Edit.
- **Field perms:** all fields above → Read + Edit (Master-Detail/required fields are implicitly editable).
- **Tabs:** `PRM_AsyncJob__c` tab → Visible (for support/monitoring).
- **Apex class access:** add the EPIC C classes (`PRM_AsyncOrchestrator`, executors, trigger handler) here **when they exist** (EPIC C) — out of scope for A.
- **Custom Metadata:** `PRM_AsyncJobConfig__mdt` is readable by Apex without perms; no entry needed.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>PRM Async Job Access</label>
    <hasActivationRequired>false</hasActivationRequired>
    <objectPermissions>
        <object>PRM_AsyncJob__c</object>
        <allowCreate>true</allowCreate><allowRead>true</allowRead>
        <allowEdit>true</allowEdit><allowDelete>true</allowDelete>
        <viewAllRecords>false</viewAllRecords><modifyAllRecords>false</modifyAllRecords>
    </objectPermissions>
    <!-- repeat for PRM_AsyncJobDetails__c; field/tab permissions per object -->
</PermissionSet>
```

---

## A6 · Deployment & sequencing

1. Objects first: `PRM_AsyncJob__c` → then `PRM_AsyncJobDetails__c` (Master-Detail needs the parent).
2. `PRM_AsyncJobConfig__mdt` type + config records (one per process: `PAR`, `Practitioner Creation`).
3. `PRM_AsyncJob_Access` permission set.
4. Command: `sf project deploy start -d force-app/main/default/objects/PRM_AsyncJob__c force-app/main/default/objects/PRM_AsyncJobDetails__c ...`

---

## A7 · Open items


| Ref                                        | Item                                                                                                     | Action                                                                                                                                                             |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| CL-6                                       | Is the high-volume target HCFN only or also `NetworkMember`/`NetworkMemberChunk`?                        | Confirm before EPIC C; may add a config record                                                                                                                     |
| Retry / circuit-breaker / retention config | `PRM_MaxRetries__c`, `PRM_Active__c`, `PRM_RetentionDays__c` were removed from `PRM_AsyncJobConfig__mdt` | **Decision:** handled as **Apex constants** in EPIC C (retry ceiling in the dispatcher; retention in the cleanup batch; circuit-breaker = manual). Confirm values. |
| `PRM_BatchSize__c` default                 | `200`                                                                                                    | Confirm with platform/ops                                                                                                                                          |


