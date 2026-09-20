# IBX - PNM - Analysis

Independence Blue Cross (IBX) Provider Network Management (PNM) analysis: user stories, SOQL, architecture notes, and implementation plans.

This repository is **documentation only**. Salesforce metadata and Apex live in the IBXQA project, not here.

## What's in this repo

| Folder | Contents |
|---|---|
| [`requirements/`](requirements/) | User stories, bug-fix stories, root-cause analyses, SOQL archive, ROM/TDD notes, vendor inventories |
| [`docs/`](docs/) | Implementation plans (Practitioner Creation / high-volume async), architecture overviews, mockups, GameChanger notes, interviews |

## Layout

```
requirements/
  *.md                         User stories and analyses
  SOQL/                        Dated SOQL knowledge base
  Enhancements/                Deeper architecture notes
  Reporting/                   Report stories
  2027_ROM_TDD/                ROM / TDD working papers
docs/
  implementation-plan/         High-volume Practitioner Creation plan + epic guides
  gamechanger/                 Factory / org-reconciliation notes
  build-verification/          Parity ledgers and agent catalogs
  interviews/                  Interview guides
```

## Origin

Copied from the IBXQA workspace (`requirements/` and `docs/`) on 2026-09-20. Agent session JSON and OS junk files were left out.
