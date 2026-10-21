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
  inputs: [tablePort],
  outputs: [tablePort],
  config_schema: { properties: { amount: { type: "integer", default: 1 } } },
};
