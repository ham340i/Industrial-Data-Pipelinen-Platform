# User consent and end-user license agreement

**Status: draft. Not reviewed by counsel, not approved by the partner and not in effect.** The application shows no consent screen today.

## Why consent is light for this product

The tool runs entirely on the user's workstation. It sends no telemetry, has no accounts and makes no outbound network connection: every source, including the SQL source, is a file inside the workspace. The data it stores is:

| Data | Where | Who can read it |
|---|---|---|
| Projects, pipeline definitions and revisions | Local SQLite file | Anyone with access to the workstation account |
| Run history: states, timings, row counts, redacted log lines | Local SQLite file | Same |
| Published outputs (CSV, Parquet) | The project's folder in the workspace the user selected | Same |

No personal information is required to use it.

## Draft terms

1. **Authorized data only.** You use the tool only with data and database accounts you are permitted to process under your organization's policy.
2. **Local storage.** Definitions, run history and outputs stay on your machine. Removing them is your responsibility; deleting the metadata file and workspace folder removes everything the tool stored.
3. **No credentials in pipelines.** Pipeline definitions reject credentials and machine paths so they can be shared. Do not work around this.
4. **Limits.** Previews are samples, not full results. Row counts the tool cannot know are shown as unknown, never as zero. The tool is not validated for safety-critical or regulatory decisions.
5. **No warranty.** The software is provided as is, without warranty, and the authors are not liable for damages arising from its use. The final wording follows the software license once one is selected; see [Legal and ethical issues](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Legal-and-Ethical-Issues).

## Decisions still required

- Whether the partner needs a click-through agreement, or whether the software license alone is enough for an internal local tool.
- Who at the partner approves the text.

The repository copy of this draft is [docs/user-consent-eula.md](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/user-consent-eula.md).
