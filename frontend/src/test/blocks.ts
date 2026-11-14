import type { BlockMetadata, Port } from "../api/blocks";
export const tablePort: Port = {
  name: "table",
  kind: "data",
  required: true,
  many: false,
  data_schema: {
    columns: [{ name: "value", dtype: "integer", nullable: false }],
    allow_extra_columns: false,
  },
};
export const sampleBlock: BlockMetadata = {
  sdk_version: 1,
  block_id: "synthetic.add_constant",
  version: "1.0.0",
  name: "Synthetic Add Constant",
  category: "synthetic",
  library_visible: false,
  inputs: [tablePort],
  outputs: [tablePort],
  config_schema: {
    type: "object",
    additionalProperties: false,
    properties: {
      amount: {
        title: "Amount",
        type: "integer",
        default: 1,
        minimum: -1000,
        maximum: 1000,
      },
    },
  },
};

// Production metadata used by library authoring tests. Keep the SDK example
// above for contract tests and compatibility with existing saved nodes.
export const rowCountBlock: BlockMetadata = {
  sdk_version: 1,
  block_id: "quality.row_count",
  version: "1.0.0",
  name: "Row Count",
  category: "quality",
  library_visible: true,
  inputs: [
    { ...tablePort, data_schema: { columns: [], allow_extra_columns: true } },
  ],
  outputs: [
    { ...tablePort, data_schema: { columns: [], allow_extra_columns: true } },
  ],
  config_schema: {
    type: "object",
    additionalProperties: false,
    properties: {
      min_rows: { title: "Min Rows", type: "integer", default: 0, minimum: 0 },
      max_rows: {
        title: "Max Rows",
        anyOf: [{ type: "integer", minimum: 0 }, { type: "null" }],
        default: null,
      },
      required: { title: "Required", type: "boolean", default: true },
    },
  },
};
