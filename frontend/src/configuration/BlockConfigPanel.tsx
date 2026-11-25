// AI contribution: 50% or more AI-generated
import {
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";
import { Alert, Button, Paper, Stack, Typography } from "@mui/material";
import {
  assertPublic,
  defaultsFor,
  fieldsFromSchema,
  validateConfiguration,
} from "./schema";
import type {
  Configuration,
  ConfigField,
  ConfigIssue,
  JsonValue,
} from "./schema";

import { ConfigFormField } from "./ConfigFormField";

export interface SelectedBlock {
  nodeId: string;
  blockId: string;
  version: string;
}
export interface RegistryBlock {
  block_id: string;
  version: string;
  name: string;
  config_schema: unknown;
}
export type RegistryState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; blocks: RegistryBlock[] };
export interface BlockConfigPanelProps {
  selected: SelectedBlock | null;
  registry: RegistryState;
  value: Configuration;
  onChange: (nodeId: string, value: Configuration) => void;
  disabled?: boolean;
  serverErrors?: Record<string, string[]>;
  staleDiagnostics?: boolean;
  focusRequest?: { nodeId: string; field: string | null } | null;
  onRetry?: () => void;
}

function RecoveryNotice({
  focusRequest,
  disabled,
  loading = false,
  children,
}: Pick<BlockConfigPanelProps, "focusRequest" | "disabled"> & {
  loading?: boolean;
  children: ReactNode;
}) {
  const noticeRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (focusRequest && !disabled) noticeRef.current?.focus();
  }, [focusRequest, disabled]);
  return (
    <Alert
      ref={noticeRef}
      tabIndex={-1}
      severity={loading ? "info" : "error"}
      role={loading ? "status" : "alert"}
    >
      {children}
    </Alert>
  );
}

function focusConfiguration(
  form: HTMLElement | null,
  requested: string | null,
) {
  if (!form) return;
  const controls = Array.from(
    form.querySelectorAll<HTMLElement>(
      "input[data-config-field]:not([type=hidden]):not([readonly]):not(:disabled), textarea[data-config-field]:not([readonly]):not(:disabled), select[data-config-field]:not(:disabled)",
    ),
  ).filter((input) => !input.closest("[hidden], [aria-hidden=true], [inert]"));
  const field = requested?.split(/[.[]/, 1)[0];
  const input = field
    ? (controls.find((input) => input.dataset.configField === requested) ??
      controls.find((input) => input.dataset.configField === field))
    : (controls.find(
        (input) => input.getAttribute("aria-invalid") === "true",
      ) ?? controls[0]);
  (input ?? form).focus();
}

function readFields(schema: unknown) {
  try {
    return fieldsFromSchema(schema);
  } catch {
    return null;
  }
}

function ConfigurationIssues({
  nodeId,
  issues,
  updateError,
}: {
  nodeId: string;
  issues: ConfigIssue[];
  updateError: string | null;
}) {
  return (
    <>
      {issues.length > 0 && (
        <Alert severity="warning" role="status">
          {issues.length} configuration{" "}
          {issues.length === 1 ? "issue needs" : "issues need"} attention for
          block {nodeId}.
        </Alert>
      )}
      {updateError && <Alert severity="error">{updateError}</Alert>}
      {issues
        .filter((issue) => !issue.field)
        .map((issue) => (
          <Alert severity="warning" key={issue.message}>
            {issue.message}
          </Alert>
        ))}
    </>
  );
}

type ConfigFormProps = Omit<
  BlockConfigPanelProps,
  "selected" | "registry" | "onRetry"
> & {
  selected: SelectedBlock;
  block: RegistryBlock;
};

function ConfigurationFields({
  nodeId,
  fields,
  effective,
  issues,
  serverErrors,
  staleDiagnostics,
  disabled,
  update,
}: {
  nodeId: string;
  fields: ConfigField[];
  effective: Configuration;
  issues: ConfigIssue[];
  serverErrors: Record<string, string[]>;
  staleDiagnostics: boolean;
  disabled: boolean;
  update: (name: string, value: JsonValue | undefined) => void;
}) {
  if (fields.length === 0)
    return <Typography>This block needs no configuration.</Typography>;
  return fields.map((field) => (
    <ConfigFormField
      key={field.name}
      field={field}
      nodeId={nodeId}
      value={effective[field.name]}
      issues={issues}
      serverErrors={serverErrors}
      staleDiagnostics={staleDiagnostics}
      disabled={disabled}
      onChange={(value) => update(field.name, value)}
    />
  ));
}

function useConfigurationUpdate(
  nodeId: string,
  onChange: BlockConfigPanelProps["onChange"],
) {
  const [updateError, setUpdateError] = useState<string | null>(null);
  function update(
    effective: Configuration,
    name: string,
    next: JsonValue | undefined,
  ) {
    const config = { ...effective };
    if (next === undefined) delete config[name];
    else config[name] = next;
    try {
      assertPublic(config);
      onChange(nodeId, config);
      setUpdateError(null);
    } catch {
      setUpdateError(
        "Use logical resource references instead of runtime bindings or credential fields. This edit was not stored.",
      );
    }
  }
  return { updateError, update };
}

function ConfigFormLayout({
  headingId,
  formRef,
  block,
  nodeId,
  children,
}: {
  headingId: string;
  formRef: RefObject<HTMLElement | null>;
  block: RegistryBlock;
  nodeId: string;
  children: ReactNode;
}) {
  return (
    <Paper
      component="section"
      ref={formRef}
      tabIndex={-1}
      aria-labelledby={headingId}
      variant="outlined"
      sx={{ p: 3 }}
    >
      <Stack spacing={2.5}>
        <div>
          <Typography id={headingId} component="h2" variant="h6">
            Configure {block.name}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Block {nodeId} · {block.version}
          </Typography>
        </div>
        {children}
        <Typography variant="caption" color="text.secondary">
          Values stay with this block when selection changes. Use resource
          references for protected data. The server validates configuration
          before execution.
        </Typography>
      </Stack>
    </Paper>
  );
}

// eslint-disable-next-line max-lines-per-function -- Keep diagnostic and field rendering together with the focusable form region they describe.
function ConfigForm({
  selected,
  block,
  value,
  onChange,
  disabled = false,
  serverErrors = {},
  staleDiagnostics = false,
  focusRequest,
}: ConfigFormProps) {
  const headingId = useId();
  const formRef = useRef<HTMLElement>(null);
  const { updateError, update } = useConfigurationUpdate(
    selected.nodeId,
    onChange,
  );
  useEffect(() => {
    if (focusRequest && !disabled)
      focusConfiguration(formRef.current, focusRequest.field);
  }, [focusRequest, disabled]);
  const fields = readFields(block.config_schema);
  if (!fields) {
    return (
      <RecoveryNotice focusRequest={focusRequest} disabled={disabled}>
        This block has an unsupported or unsafe configuration schema. Existing
        values have been preserved. Ask the block owner to provide a supported
        public schema.
      </RecoveryNotice>
    );
  }
  const effective = { ...defaultsFor(fields), ...value };
  const issues = validateConfiguration(fields, effective);
  return (
    <ConfigFormLayout
      formRef={formRef}
      headingId={headingId}
      block={block}
      nodeId={selected.nodeId}
    >
      <ConfigurationIssues
        nodeId={selected.nodeId}
        issues={issues}
        updateError={updateError}
      />
      <ConfigurationFields
        nodeId={selected.nodeId}
        fields={fields}
        effective={effective}
        issues={issues}
        serverErrors={serverErrors}
        staleDiagnostics={staleDiagnostics}
        disabled={disabled}
        update={(name, next) => update(effective, name, next)}
      />
    </ConfigFormLayout>
  );
}

function registryNotice({
  status,
  focusRequest,
  disabled,
  onRetry,
}: Pick<BlockConfigPanelProps, "focusRequest" | "disabled" | "onRetry"> & {
  status: "loading" | "error";
}) {
  const loading = status === "loading";
  return (
    <RecoveryNotice
      focusRequest={focusRequest}
      disabled={disabled}
      loading={loading}
    >
      {loading
        ? "Loading block definitions. Your configuration is preserved."
        : "Block definitions could not be loaded. Your configuration is preserved."}
      {!loading && onRetry && (
        <Button onClick={onRetry}>Retry definitions</Button>
      )}
    </RecoveryNotice>
  );
}

export function BlockConfigPanel({
  selected,
  registry,
  onRetry,
  ...props
}: BlockConfigPanelProps) {
  if (!selected)
    return (
      <Paper variant="outlined" sx={{ p: 3 }}>
        <Typography component="h2" variant="h6">
          Block configuration
        </Typography>
        <Typography sx={{ mt: 1 }}>Select a block to configure it.</Typography>
      </Paper>
    );
  if (registry.status !== "ready")
    return registryNotice({
      status: registry.status,
      focusRequest: props.focusRequest,
      disabled: props.disabled,
      onRetry,
    });
  const matches = registry.blocks.filter(
    (item) =>
      item.block_id === selected.blockId && item.version === selected.version,
  );
  if (matches.length !== 1)
    return (
      <RecoveryNotice
        focusRequest={props.focusRequest}
        disabled={props.disabled}
      >
        The exact block version is unavailable or duplicated. Your configuration
        is preserved.
      </RecoveryNotice>
    );
  return (
    <ConfigForm
      key={`${selected.nodeId}:${selected.blockId}:${selected.version}`}
      {...props}
      selected={selected}
      block={matches[0]}
    />
  );
}
