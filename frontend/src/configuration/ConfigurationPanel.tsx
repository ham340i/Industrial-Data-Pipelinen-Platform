import { Alert, Box } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { getBlocks } from "../api/blocks";
import type { Diagnostic } from "../api/validation";
import { useEditorStore } from "../state/editor";
import { fieldMessages } from "../state/validation";
import { BlockConfigPanel, type RegistryState } from "./BlockConfigPanel";
import { assertPublic } from "./schema";

export function ConfigurationPanel({
  diagnostics = [],
}: {
  diagnostics?: Diagnostic[];
}) {
  const selectedId = useEditorStore((s) => s.selectedNodeId);
  const node = useEditorStore((s) =>
    s.nodes.find((n) => n.id === s.selectedNodeId),
  );
  const onChange = useEditorStore((s) => s.setNodeConfiguration);
  const busy = useEditorStore((s) => s.busy);
  const focus = useEditorStore((s) => s.configFocus);
  const catalog = useQuery({
    queryKey: ["blocks"],
    queryFn: ({ signal }) => getBlocks(signal),
    retry: false,
  });
  const registry: RegistryState = catalog.isPending
    ? { status: "loading" }
    : catalog.isError
      ? { status: "error" }
      : { status: "ready", blocks: catalog.data };
  const config = node?.data.config ?? {};
  try {
    assertPublic(config);
  } catch {
    return (
      <Alert severity="error">
        Block {selectedId}: configuration contains unsupported values or runtime
        bindings. Use resource references; the stored draft has not been
        changed.
      </Alert>
    );
  }
  return (
    <Box
      component="aside"
      aria-label="Block configuration"
      sx={{ minWidth: 0 }}
    >
      <BlockConfigPanel
        selected={
          node
            ? {
                nodeId: node.id,
                blockId: node.data.block_id,
                version: node.data.block_version,
              }
            : null
        }
        registry={registry}
        value={config}
        onChange={onChange}
        disabled={busy}
        serverErrors={node ? fieldMessages(diagnostics, node.id) : {}}
        focusRequest={focus?.nodeId === node?.id ? focus : null}
        onRetry={() => void catalog.refetch()}
      />
    </Box>
  );
}
