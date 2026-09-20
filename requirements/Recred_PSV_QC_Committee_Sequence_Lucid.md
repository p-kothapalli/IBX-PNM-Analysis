# ReCredentialing — Sequence diagram for Lucidchart

Lucidchart cannot be generated as a binary file from this repo. Use one of these:

| Method | Steps |
|--------|--------|
| **Mermaid → image** | Copy the code block below → [mermaid.live](https://mermaid.live) → **Actions → PNG/SVG** → In Lucid: **Insert → Image**. |
| **Mermaid import** | Lucidchart **Import** (Enterprise / add-on): choose **Mermaid** and paste the same block. |
| **Manual** | Lucid **Template → Sequence diagram**; add lifelines matching the `participant` names below; mirror messages left-to-right. |

**Source metadata:** `PRM_RecredQC_English`, `PRM_NonRoutineCommitteeReview_English` DataPacks in `vlocity_export/OmniScript/`.

---

## Diagram 1 — Recred PSV + QC + save (main OmniScript)

Shows reviewer ↔ OmniScript ↔ Integration Procedures / DataRaptor ↔ Salesforce. External systems (CAQH, NPPES, FSMB, etc.) are collapsed as **External APIs** where the script calls validation/fetch IPs.

```mermaid
sequenceDiagram
  autonumber
  actor Rev as PSV / QC Reviewer
  participant OS as OmniScript<br/>PRM_RecredQC
  participant DR as DataRaptor<br/>(Transform / extract)
  participant IP as Integration<br/>Procedures
  participant SF as Salesforce<br/>Case & related
  participant EXT as External APIs<br/>(CAQH, NPPES, etc.)

  Rev->>OS: Launch from Case — Recred PSV QC Review
  OS->>OS: SetFlowVariables
  OS->>IP: IPFetchParInformation (case / PAR context)
  IP-->>SF: Query Case, Account, PAR…
  SF-->>IP: Records
  IP-->>OS: JSON context
  OS->>DR: DRTransformGroupData
  DR-->>OS: Transformed bundle

  alt Invalid case
    OS-->>Rev: InvalidCase / InvalidCaseError
    Rev-->>OS: Acknowledge / exit
  else Valid case
    OS->>OS: SetValuesReviewSubmit → ReviewSubmit
    Rev->>OS: Submit review gate

    loop Application review — ReviewPractitioner
      OS-->>Rev: Demographics, specialties, addresses, DEI, contacts…
      Rev->>OS: Confirm / Next
    end
    OS->>OS: SetPractitionerSpecialtyFields

    OS->>DR: DRTransformPSVScreenData, DRTransformReCredData
    DR-->>OS: PSV screen payload

    loop PSV — Primary Source Verification
      OS-->>Rev: PSV blocks (NPI, CAQH attestation, SAV, licenses…)
      Rev->>OS: Verify / attest / upload
      OS->>IP: IPValidateNPI, IPValidateCAQHAppReviewParent, IPGetPracticeLocation…
      IP->>EXT: NPPES / CAQH / other
      EXT-->>IP: Responses
      IP-->>OS: Validation result
      opt CAQH / practice transform
        OS->>DR: DRTransformCAQHPSVResponse
        DR-->>OS: Normalized CAQH fields
      end
      opt Specialty failure path
        OS->>IP: IPUpdateSpecailtyReviewResult
        IP->>SF: Update review outcome
      end
    end

    OS-->>Rev: PSVSummary → ReCredPSVSummary (read-only columns)
    Rev->>OS: Proceed / notes

    loop QC review
      OS-->>Rev: QCReviewSummary
      alt Return to PSV
        Rev->>OS: QCReturnTo
        OS-->>Rev: Prior PSV / review steps
      else Proceed
        Rev->>OS: QCProceedTo → QCProceedToNote
        opt Missing-info ContentNote
          OS->>SF: Create ContentNote (template / ReCred)
        end
      end
    end

    OS-->>Rev: MDRFormStep (Medical Director fields)
    Rev->>OS: Complete MDR section

    OS->>OS: SetRecord* (PSV/QC/Recred flags)<br/>SetQCReadyForCommittee / MedicalReview…
    OS->>IP: IPUpdateRecredReviewUpdate
    IP->>SF: Upsert Case / review fields
    SF-->>IP: Success / fault
    alt Save OK
      IP-->>OS: OK
      OS-->>Rev: NavigateToCaseManager
    else Save error
      IP-->>OS: Error
      OS-->>Rev: ResultPSVReviewError / UpdateFailed
    end
  end
```

---

## Diagram 2 — Non-routine committee (separate OmniScript)

Use when the case moves to committee / SVNR outcomes after QC (or parallel track).

```mermaid
sequenceDiagram
  autonumber
  actor Com as Committee / CM User
  participant OS2 as OmniScript<br/>NonRoutineCommitteeReview
  participant IP2 as Integration<br/>Procedures
  participant SF as Salesforce<br/>Case

  Com->>OS2: Open committee OmniScript
  OS2->>OS2: SetFlowType
  OS2->>IP2: IPToFetchRoutineCaseDetails
  IP2->>SF: Load case / committee context
  SF-->>IP2: Data
  IP2-->>OS2: Payload

  alt Invalid case
    OS2-->>Com: InvalidCase → TBInvalidCase
  else Valid
    OS2->>SF: UpdateCaseStatus (via SetValues / step)
    OS2-->>Com: CaseStatus / CaseStatusRecred, denial, dates, RecredDueDate…

    loop Outcome branch (SVNR*)
      Com->>OS2: Select path — Sent to Committee / Approved / Denied / Appeal / MD pending / Outreach / Specialist / Due process
      OS2->>OS2: Conditional SetValues per branch
    end

    OS2->>IP2: IPNonroutineRecordsUpdate
    IP2->>SF: Persist committee outcome
    SF-->>IP2: Result
    alt Success
      IP2-->>OS2: OK
      OS2-->>Com: NavigateCaseManager
    else Error
      OS2-->>Com: ErrorStep
    end
  end
```

---

## Lucidchart manual checklist (if not using Mermaid)

**Lifelines (left → right):** Reviewer | OmniScript RecredQC | DataRaptor | Integration Procedures | Salesforce | External APIs  

**Fragment boxes:** `alt` Invalid case | `loop` Application review | `loop` PSV | `alt` QC return vs proceed | `opt` ContentNote | `alt` Save OK vs error  

**Second page:** Committee user | NonRoutine OmniScript | IP | Salesforce | same `alt`/`loop` pattern for SVNR branches.

---

## See also

- `requirements/Recred_PSV_QC_Committee_Lucid_Flowchart.md` — detailed flowchart + step list.
