# USER STORY: Allow Email Files (.eml / .msg) in the Document Upload Flow

**Persona:** Credentialing Specialist (also used by PDM Specialist — `PRM_FileUploadOS` is a shared upload flow)
**Priority:** P1
**OmniScript:** `PRM_FileUploadOS_English` (active v10)
**Integration Procedures:** `PRM_FileValidationParent` (v1) → `PRM_FileValidation` (active v6)
**Apex:** `PRM_OmniUtils.validateFiles`
**Relevant Requirements:** `requirements/File_Upload_Size_Increase_15MB_to_100MB.md` (related — file-size limit), `requirements/Enhancements/practitionerCreation/PractitionerCreation_FileUpload_DesignPlan.md`

---

## Story

**As a** Credentialing Specialist,
**I want** to attach email files (such as `.eml` and `.msg`) in the document upload step,
**So that** I can retain correspondence from providers and internal teams as part of the case documentation without having to first convert each email to PDF.

**Why it matters:** Today the upload flow rejects everything except PDF, Excel, and CSV. Specialists routinely receive provider correspondence as Outlook/email files and must manually print-to-PDF before uploading, which is slow and loses email metadata (sender, date, headers). Allowing native email files removes a manual conversion step and preserves the original document of record.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|--------------|-------------|
| Document Upload (Credentialing & PDM) | `PRM_FileUploadOS_English` | `FileDocumentation` step → `FileBlock` (File element) | `PRM_FileValidationParent` → `PRM_FileValidation` → `PRM_OmniUtils.validateFiles` |

---

## Current State (from codebase)

### `PRM_FileUploadOS_English` (v10)

- **`FileUpload`** (File element): no client-side `accept` filter is configured — the browser file picker already lets the user choose any file; restriction is enforced server-side only.
- **`TBFileErrorMsg`** (Text Block): displays *"File must be in PDF or Excel format only and file size must not exceed 15mb."* when `FileValidSuccess = false`.
- **`SerErrorFileValidation`** (Set Errors): maps the same message text onto `TBFileErrorMsg`.
- **`IPPRMFileValidation`** (Integration Procedure Action): calls `PRM_FileValidationParent`, passing the uploaded `FileBlock` details.

### `PRM_FileValidation` (v6)

- **`RActionValidateFileName`** (Remote Action → `PRM_OmniUtils.validateFiles`): passes the allow-list
  `formats = [".pdf", ".xlsx", ".xls", ".csv"]` and `MaxSize = 15728640` (15 MB).
- **`RAFileValidation`** (Response Action): sets `FileValidSuccess = false` when Apex returns any `inValidFiles`.

### `PRM_OmniUtils.validateFiles` (Apex)

- Extracts the file extension from the **last 4 characters** of the filename (special-cases 5-char `.xlsx`), lowercases the allow-list, and marks any file whose extension is not in the allow-list (or exceeds `MaxSize`) as invalid.
- **Key finding:** `.eml` and `.msg` are both 4-character extensions, so they are handled by the existing generic extension logic. **No Apex change is required** — only the `formats` allow-list and the user-facing messages need to change.

---

## Acceptance Criteria

**AC-1 — Specialist can upload an email file**

**Given** a Credentialing Specialist is on the Upload Documentation step and has selected a document type,
**When** they attach an email file (`.eml` or `.msg`) within the size limit and continue,
**Then** the file is accepted and saved against the case like any other supported document,
**And** no file-format error is shown.

**AC-2 — Mixed batch with an email file succeeds**

**Given** a Credentialing Specialist attaches a PDF, an Excel file, and an email file together for the same document type,
**When** they continue,
**Then** all three files are accepted and saved,
**And** no file-format error is shown.

**AC-3 — Unsupported file types are still rejected**

**Given** a Credentialing Specialist attaches a file that is not a supported type (for example a `.docx`, `.png`, or `.zip`),
**When** they continue,
**Then** the upload is blocked,
**And** the error message lists the now-supported formats including email files.

**AC-4 — Updated guidance message reflects email support**

**Given** a Credentialing Specialist triggers a file-format validation error,
**When** the error message is displayed,
**Then** it reads as the agreed wording, e.g. *"File must be in PDF, Excel, CSV, or Email (.eml/.msg) format only and file size must not exceed 15mb."*
**And** the same wording appears wherever the file-format error is shown in the flow.

**AC-5 — File-size limit is unchanged**

**Given** a Credentialing Specialist attaches an email file that exceeds the current size limit (15 MB),
**When** they continue,
**Then** the file is rejected with the size/format error,
**And** the email-file enhancement does not change the existing size limit.

**AC-6 — Per-document-type file count limit is unchanged**

**Given** a Credentialing Specialist has already attached the maximum allowed files for one document type,
**When** they attach an additional email file under the same document type,
**Then** the existing "file limit exceeded" behavior applies unchanged.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_FileValidation` | New IP version (v7) | In the `RActionValidateFileName` step, change `formats` from `[".pdf", ".xlsx", ".xls", ".csv"]` to `[".pdf", ".xlsx", ".xls", ".csv", ".eml", ".msg"]` | Drives AC-1, AC-2, AC-3. Activate v7 so `PRM_FileValidationParent` (which calls IP key `PRM_FileValidation`) picks it up. |
| `PRM_FileUploadOS_English` | New OmniScript version (v11) | Update message text in `TBFileErrorMsg` (Text Block) and in `SerErrorFileValidation` (Set Errors `elementErrorMap`) to the agreed email-inclusive wording | Drives AC-4. Activate v11. |
| `PRM_OmniUtils.validateFiles` | Apex — verify only | No change required; `.eml`/`.msg` are 4-char extensions handled by existing logic | Confirm with a unit-test case for an `.eml` filename. |
| `PRM_OmniUtils` test class | Test update | Add coverage for an `.eml`/`.msg` filename returning a valid result | Regression guard. |

> Note: the `File` element has no client-side `accept` MIME filter today, so no change there is strictly required. Optionally, if the team wants the OS picker to *visually* hint email support, an `accept` value could be added — track as a separate decision (see Clarification Q3).

---

## Definition of Done

- [ ] `PRM_FileValidation` v7 active with the expanded `formats` allow-list.
- [ ] `PRM_FileUploadOS_English` v11 active with the updated error wording in both message locations.
- [ ] Uploading `.eml` and `.msg` succeeds in QA across both Credentialing and PDM entry points.
- [ ] Unsupported types still rejected; size and per-type count limits unchanged.
- [ ] `PRM_OmniUtils` test class updated and passing.
- [ ] Verified the saved email file is downloadable/openable from the case after upload.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Which email formats does business need — `.eml` only, `.msg` only, or both? | Determines exact `formats` entries | BA / Product |
| 2 | Exact approved wording for the updated error message? | AC-4 message text | BA / Product |
| 3 | Should the OmniScript File picker also add a client-side `accept` filter, or keep server-side-only validation (current behavior)? | UX of the file chooser | Technical / UX |
| 4 | Do email files share the same 15 MB size limit, or do they need a different limit (note the in-flight 15→100 MB story)? | AC-5 / `MaxSize` | Product / Ops |
| 5 | Does this apply to every flow that embeds `PRM_FileUploadOS` (Credentialing, PDM, etc.), or a subset? | Rollout scope | BA / Product |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| `PRM_FileValidation` | Integration Procedure | MEDIUM | Allow-list change; shared by all flows embedding the upload OS |
| `PRM_FileUploadOS_English` | OmniScript | MEDIUM | New active version; reused across Credentialing & PDM |
| `PRM_OmniUtils` | Apex | LOW | No logic change; test coverage only |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| `PRM_FileValidation` (v7) | IP `formats` array edit + activate | S | AI-estimated — validate with team |
| `PRM_FileUploadOS_English` (v11) | OmniScript message text edit + activate | S | AI-estimated — two text locations |
| `PRM_OmniUtils` test | Apex test add | S | AI-estimated |
| QA across entry points | Manual verification | M | Credentialing + PDM |

**Total Estimated Effort:** ~S–M (config/metadata change, no new Apex logic) — **AI-estimated, validate with team**
