import type { BlockMetadata } from "../api/blocks";
import type { PreviewRequest, PreviewResult } from "../api/preview";

export const csvBlock: BlockMetadata = {
  sdk_version: 1,
  block_id: "source.csv",
  version: "1.0.0",
  name: "CSV Source",
  category: "source",
  block_type: "source",
  supports_preview: true,
  preview_reason: null,
  inputs: [],
  outputs: [
    {
      name: "table",
      kind: "data",
      required: true,
      many: false,
      data_schema: { columns: [], allow_extra_columns: true },
    },
  ],
  config_schema: {
    type: "object",
    properties: { resource_ref: { type: "string" } },
  },
};
export function previewResult(request: PreviewRequest): PreviewResult {
  return {
    node_id: request.node_id,
    output_port: request.output_port,
    data_schema: {
      columns: [{ name: "value", dtype: "string", nullable: true }],
      allow_extra_columns: false,
    },
    rows: [{ value: "sample-value" }, { value: null }],
    sample_row_count: 2,
    sample_cell_count: 2,
    inspected_row_count: 3,
    full_row_count: null,
    full_count_scope: "unknown",
    truncated: true,
    sampling_method: "leading_rows",
    schema_scope: "header",
    null_scope: "returned_sample",
    nulls: [{ column: "value", null_count: 1 }],
    effective_limits: request.limits,
    source_read_bytes: 30,
    elapsed_ms: 1,
    evaluated_node_ids: [request.node_id],
  };
}
