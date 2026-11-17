# Legal and ethical issues

## Legal record

| Item | Status | Reference |
|---|---|---|
| Software license | **Not selected.** No `LICENSE` file exists, so no rights are granted to anyone yet. The course recommends MIT because it assigns copyright to the authors and disclaims liability. | Decision needed from the team and partner |
| Concordia IP opt-out | Not required if the MIT license is adopted. Otherwise it is uploaded to Moodle and never committed here. | Not in this repository by design |
| Stakeholder agreement and liability clause | Not recorded | To be uploaded where the course requires, not committed here |
| NDA | Not recorded; applicability undecided | Same |
| Third-party code | We found no vendored or copied third-party source in the repository. Dependencies are installed from their registries and listed in [Infrastructure and tools](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Infrastructure-and-Tools) | [requirements.txt](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/requirements.txt), [package.json](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/frontend/package.json) |

Signed documents contain personal information and stay out of Git.

## Ethical issues

- **Honest data quality.** A pipeline tool can make bad data look finished. The product refuses to guess: casts that would lose precision fail, integer sums that overflow fail, previews are labelled as samples, and unknown row counts are shown as unknown. Data-quality blocks can stop a run instead of passing bad rows on ([data quality](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/data-quality.md)).
- **Confidential manufacturing data.** Partner data may be export-controlled or commercially sensitive. The tool keeps data on the workstation, redacts credentials and machine paths from logs, and the repository contains synthetic fixtures only. See [Security](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Security).
- **Honest reporting.** Project records state what is unfinished: no stakeholder signoff, no license, open Release 1 items. AI assistance is declared per file, per pull request and in the [AI usage record](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/.github/AI_USAGE.md).
- **Privacy of team members.** The repository holds GitHub usernames only; student IDs and contact details are kept out.

## Environment

Processing runs on existing workstations; no cloud compute is provisioned. Fixed limits on rows, cells, bytes and query memory stop a mistaken pipeline from consuming a machine for hours. CI cancels superseded runs for the same branch.

## Discrimination and minority groups

The tool processes manufacturing data, not data about people, and makes no decisions about individuals. The equity concern is who can use it; see the [Diversity statement](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Diversity-Statement).

## Impact on jobs

The tool automates repetitive data preparation that process specialists do by hand or with one-off scripts. It is designed to keep the specialist in control: they author the pipeline, see each step's sample and decide what is published. It can reduce demand for ad hoc scripting work; it also lets specialists without programming training do work that previously needed a developer. We have not measured either effect.
