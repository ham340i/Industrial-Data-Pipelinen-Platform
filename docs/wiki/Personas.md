# Personas

These personas come from the project brief. They have not been validated in interviews with the partner; that validation is an open action.

## Priya, process specialist (primary)

- **Goal:** turn raw machine and inspection exports into a clean table she can analyse, every week, without asking a developer.
- **Background:** deep process knowledge; comfortable with spreadsheets; little or no programming.
- **Pain today:** repeats the same clean-up by hand; cannot see where a transformation went wrong.
- **What she uses:** the visual builder, block library, configuration forms, preview of each step and plain-language validation errors.

## Daniel, data and systems integrator

- **Goal:** connect approved source systems and keep data contracts stable.
- **Background:** SQL and schemas; cautious about access.
- **Pain today:** schema drift and scripts nobody else can maintain.
- **What he uses:** the read-only SQL source, declared column schemas, data-quality blocks and portable pipeline definitions he can review.

## Elena, engineering analyst and ML consumer

- **Goal:** trust that a dataset is the same one that was validated.
- **Pain today:** no provenance; inputs change silently.
- **What she uses:** governed Parquet artifacts with recorded schema, producing run and pipeline revision; bounded queries over an artifact.

## Sam, workstation administrator

- **Goal:** install and run the tool without opening the network or storing secrets in files.
- **What he uses:** the Compose workspace, loopback-only ports, the allowed-workspace-folder setting and the run log.

## How the personas shaped the product

| Decision | Persona |
|---|---|
| Configuration forms are generated from each block's schema, so every block is configurable without code | Priya |
| Errors name the block and field and offer a retry that keeps unsaved edits ([#33](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/33)) | Priya |
| Definitions cannot hold credentials or machine paths | Daniel, Sam |
| Outputs are registered with schema and provenance before they can be queried ([#28](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/28)) | Elena |
